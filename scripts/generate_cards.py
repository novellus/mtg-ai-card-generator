import argparse
import json
import math
import os
import pprint
import random
import re
import subprocess

from collections import defaultdict
from PIL import Image


# Constants
CONDA_ENV_SD = 'ldm'
CONDA_ENV_MTGENCODE = 'mtgencode'
PATH_TORCH_RNN = '../torch-rnn'
PATH_SD = '../stable-diffusion'
PATH_MTGENCODE = '../mtgencode'
# average lengths, for initial LSTM sample length target
LSTM_LEN_PER_NAME =      math.ceil(439024  / (26908 + 135))  # empirical, change if the dataset changes
LSTM_LEN_PER_MAIN_TEXT = math.ceil(4373216 / (23840 + 119))  # empirical, change if the dataset changes
LSTM_LEN_PER_FLAVOR =    math.ceil(2048192 / (19427 + 117))  # empirical, change if the dataset changes



def sample_lstm(nn_path, seed, approx_length_per_chunk, num_chunks, delimiter, parser=None, initial_length_margin=1.05, trimmed_delimiters=2, deduplicate=True, max_resamples=3, length_growth=2, whisper_text=None, whisper_every_newline=1, verbosity=0):
    # samples from nn at nn_path with seed
    #   whispers whisper_text if specified, at interval whisper_every_newline
    # initially samples a length of characters targeting the number of chunks with margin
    # chunks on delimiter
    # trims trimmed_delimiters chunks from both beginning and end of stream
    # optionally deduplicates chunks
    # optionally parses chunks with given function
    #   if parser raises an error, the chunk is discarded
    # checks for atleast num_chunks remaining
    #   resamples at geometrically higher lengths (*length_growth) if criterion not met
    #   raises error if max_resamples exceeded
    # trims to num_chunks
    # returns list of chunks

    # set total sample length, including trimmed portion
    length = approx_length_per_chunk * (num_chunks + 2 * trimmed_delimiters) * initial_length_margin
    length = math.ceil(length)

    # sample nn
    for _ in range(max_resamples):
        cmd = ( 'th sample.lua'
               f' -checkpoint "{nn_path}"'
               f' -length {length}'
               f' -seed {seed}'
              )
        if whisper_text is not None:
            cmd += (f' -whisper_text "{whisper_text}"'
                    f' -whisper_every_newline {whisper_every_newline}'
                   )

        p = subprocess.run(cmd,
                           shell=True,
                           capture_output=True,
                           check=True,
                           cwd=os.path.join(os.getcwd(), PATH_TORCH_RNN))
        sampled_text = p.stdout.decode('utf-8')

        # delimit and trim
        chunks = sampled_text.split(delimiter)

        if trimmed_delimiters > 0:
            chunks = chunks[trimmed_delimiters : -trimmed_delimiters]

        # deduplicate, but preserve order from the original input, for output stability over many runs
        if deduplicate:
            chunks = sorted(set(chunks), key=lambda x: chunks.index(x))

        if parser is not None:
            new_chunks = []
            for chunk in chunks:
                try:
                    new_chunk = parser(chunk, verbosity)
                    new_chunks.append(new_chunk)
                except:
                    pass
            chunks = new_chunks

        # check criterion
        if len(chunks) >= num_chunks:
            # trim to target number
            return chunks[:num_chunks]
        else:
            length *= length_growth

    raise ValueError(f'LSTM {nn_path} sample did not meet delimiter criterion at {length} length, exceeded {max_resamples} resamples')


def parse_flavor(chunk, verbosity=0):
    s = re.search(r'^.+\|(.+)$', chunk)
    assert s is not None

    flavor = s.group(1)
    return flavor


def parse_mtg_cards(chunk, verbosity=0):
    # use mtgencode to decode the machine encoded card format, producing nice human readable fields

    # escape double quotes for bash string encoding
    chunk = re.sub('"', '\x22', chunk)

    cmd = ( 'python decode.py'
           f' -instring "{chunk}"'
            ' -e named'
            ' -out_encoding none'
            ' -to_json'
          )

    try:
        p = subprocess.run(f'conda run -n {CONDA_ENV_MTGENCODE} {cmd}',
                           shell=True,
                           capture_output=True,
                           check=True,
                           cwd=os.path.join(os.getcwd(), PATH_MTGENCODE))
    except subprocess.CalledProcessError as e:
        if verbosity > 1:  # we expect this to happen sometimes, and don't need to report it at low verbosity
            print('CalledProcessError in parse_mtg_cards, discarding this chunk')
            print(f'\tchunk: "{chunk}"')
            print(f'\te.stdout: "{e.stdout}"')
            print(f'\te.stderr: "{e.stderr}"')
        raise
    decoded_text = p.stdout.decode('utf-8')

    j = json.loads(decoded_text)
    j = j[0]  # we asked a batch decoder to operate on only one card

    return j


def sample_txt2img(card, outdir, seed, verbosity):
    # get outdir directory relative to command execution, rather than this script
    outdir_rel = os.path.relpath(outdir, start=PATH_SD)

    # remove temp file if it already exists, we only need one at a time
    temp_file_path = os.path.join(outdir, 'tmp.png')
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)

    if verbosity > 1:
        print(f'saving temp image file to {outdir_rel} = {temp_file_path}')

    # execute txt2img
    prompt = card['name']

    cmd = (f'python optimizedSD/optimized_txt2img.py'
           f' --ckpt models/ldm/stable-diffusion-v1/sd-v1-4.ckpt'
           f' --outdir "{outdir_rel}"'
           f' --out_filename "tmp.png"'
           f' --n_samples 1'
           f' --n_iter 1'
           f' --H 960'
           f' --W 768'
           f' --seed {seed}'
           # f' --turbo'  # encourages cinnamon crashes...
           f' --prompt "{prompt}"'
          )

    try:
        p = subprocess.run(f'conda run -n {CONDA_ENV_SD} {cmd}',
                           shell=True,
                           capture_output=True,
                           check=True,
                           cwd=os.path.join(os.getcwd(), PATH_SD))
    except subprocess.CalledProcessError as e:
        if verbosity > -1:  # always report this, since it is not caught at a higher level
            print('CalledProcessError in sample_txt2img')
            print(f'\tprompt: "{prompt}"')
            print(f'\te.stdout: "{e.stdout}"')
            print(f'\te.stderr: "{e.stderr}"')
        raise

    # open temp file, delete it, and return the image object
    im = Image.open(temp_file_path)
    os.remove(temp_file_path)
    return im


def resolve_folder_to_checkpoint_path(path):
    # return immediately if its a file
    if os.path.isfile(path):
        return path
    assert os.path.isdir(path)

    # search directory for latest checkpoint (measured in epochs trained (eg nubmer in file name))
    #   not recursive
    #   Consider parsing json file and using lowest validtion or training losses instead?
    latest_epoch = -1
    latest_checkpoint = None
    for root, dirs, files in os.walk(path):
        for f_name in files:
            s = re.search(r'checkpoint_([\d\.]+)\.t7', f_name)
            if s is not None:
                epoch = float(s.group(1))
                if epoch > latest_epoch:
                    latest_epoch = epoch
                    latest_checkpoint = os.path.join(root, f_name)

    assert latest_checkpoint is not None
    return latest_checkpoint


def main(args):
    # assign seed
    if args.seed < 0:
        args.seed = random.randint(0, 1000000000)
        if args.verbosity > 1:
            print(f'setting seed to {args.seed}')

    # resolve folders to checkpoints
    args.names_nn = resolve_folder_to_checkpoint_path(args.names_nn)
    args.main_text_nn = resolve_folder_to_checkpoint_path(args.main_text_nn)
    args.flavor_nn = resolve_folder_to_checkpoint_path(args.flavor_nn)

    # resolve and create outdir
    base_count = len(os.listdir(args.outdir))
    args.outdir = os.path.join(args.outdir, f'{base_count:05}_{args.seed}')
    os.makedirs(args.outdir)

    if args.verbosity > 2:
        print(f'operating in {args.outdir}')

    # sample names
    if args.verbosity > 1:
        print(f'sampling names')

    names = sample_lstm(nn_path = args.names_nn,
                        seed = args.seed,
                        approx_length_per_chunk = LSTM_LEN_PER_NAME,
                        num_chunks = args.num_cards,
                        delimiter = '\n',
                        verbosity = args.verbosity)

    cards = []

    # sample main text and flavor text
    for i_name, name in enumerate(names):
        if args.verbosity > 0:
            print(f'Generating {i_name + 1} / {args.num_cards}')
        if args.verbosity > 1:
            print(f'sampling main_text')

        sampled_cards = sample_lstm(nn_path = args.main_text_nn,
                                    seed = args.seed,
                                    approx_length_per_chunk = LSTM_LEN_PER_MAIN_TEXT,
                                    num_chunks = 1,
                                    delimiter = '\n\n',
                                    parser=parse_mtg_cards,
                                    whisper_text = f'|1{name}|',
                                    whisper_every_newline = 2,
                                    verbosity = args.verbosity)
        card = sampled_cards[0]  # includes the name field whispered to the nn

        if args.verbosity > 1:
            print(f'sampling flavor')

        flavors = sample_lstm(nn_path = args.flavor_nn,
                              seed = args.seed,
                              approx_length_per_chunk = LSTM_LEN_PER_FLAVOR,
                              num_chunks = 1,
                              delimiter = '\n',
                              parser=parse_flavor,
                              whisper_text = f'{name}|',
                              whisper_every_newline = 1,
                              verbosity = args.verbosity)
        card['flavor'] = flavors[0]

        cards.append(card)

        if args.verbosity > 1:
            print(f'sampling txt2img')

        sample_txt2img(card, args.outdir, args.seed, args.verbosity)

    pprint.pprint(cards)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--names_nn", type=str, help="path to names nn checkpoint, or path to folder with checkpoints (uses longest trained)")
    parser.add_argument("--main_text_nn", type=str, help="path to main_text nn checkpoint, or path to folder with checkpoints (uses longest trained)")
    parser.add_argument("--flavor_nn", type=str, help="path to flavor nn checkpoint, or path to folder with checkpoints (uses longest trained)")
    parser.add_argument("--outdir", type=str, help="path to outdir. Files are saved in a subdirectory based on seed")
    parser.add_argument("--num_cards", type=int, help="number of cards to generate, default 1", default=10)
    parser.add_argument("--seed", type=int, help="if negative or not specified, a random seed is assigned", default=-1)
    parser.add_argument("--generate_statistics", action='store_true', help="compute and store statistics over generated cards as yaml file in outdir")
    parser.add_argument("--verbosity", type=int, default=1)
    args = parser.parse_args()

    main(args)
