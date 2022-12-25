import argparse
import datetime
import functools
import math
import os
import pprint
import random
import re
import shlex
import subprocess
import yaml

# local imports
import encode
import render


# Constants
PATH_TORCH_RNN = '../torch-rnn'
PATH_SD = '../stable-diffusion'

# average lengths, for initial LSTM sample length target
LSTM_LEN_PER_MAIN_TEXT = 171  # average and empirical, change if the dataset changes (eg rebuild_data_sources.sh)
LSTM_LEN_PER_NAME =      16   # average and empirical, change if the dataset changes (eg rebuild_data_sources.sh)
LSTM_LEN_PER_FLAVOR =    105  # average and empirical, change if the dataset changes (eg rebuild_data_sources.sh)


# mana_cost_to_human_readable = {'B': 'black',
#                                'C': 'colorless_only',
#                                'E': 'energy',
#                                'G': 'green',
#                                'P': 'phyrexian',
#                                'R': 'red',
#                                'S': 'snow',
#                                'U': 'blue',
#                                'W': 'white',
#                                'X': 'X',
#                                # '\d': 'colorless',  # handled programatically
#                               }



def sample_lstm(nn_path, seed, approx_length_per_chunk, num_chunks, delimiter='\n', parser=None, initial_length_margin=1.05, trimmed_delimiters=2, deduplicate=True, max_resamples=3, length_growth=2, whisper_text=None, whisper_every_newline=1, verbosity=0):
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
    # returns list of chunks, or the returns the only chunk directly if num_chunks == 1.

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

        # trim leading / trailing whitepsace
        chunks = [x.strip() for x in chunks]

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
            chunks = chunks[:num_chunks]

            # return either a list of many, or only a single item
            if num_chunks == 1:
                return chunks[0]
            else:
                return chunks

        else:
            # try again with a longer sample
            length *= length_growth

    raise ValueError(f'LSTM {nn_path} sample did not meet delimiter criterion at {length} length, exceeded {max_resamples} resamples')


def resolve_folder_to_checkpoint_path(path, ext='t7'):
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
            s = re.search(rf'checkpoint_([\d\.]+)\.{ext}', f_name)
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

    # create / query info text components
    timestamp = datetime.datetime.utcnow().isoformat(sep=' ', timespec='seconds')

    repo_link = None
    try:
        p = subprocess.run('git remote show origin', shell=True, capture_output=True, check=True, cwd=os.getcwd())
        sampled_text = p.stdout.decode('utf-8')
        repo_link = re.search('Fetch URL: ([^\n]+)\n', sampled_text).group(1)
    except:
        repo_link = 'https://github.com/novellus/mtg-ai-card-generator'

    repo_hash = None
    try:
        p = subprocess.run('git rev-parse HEAD', shell=True, capture_output=True, check=True, cwd=os.getcwd())
        repo_hash = p.stdout.decode('utf-8').strip()
    except:
        repo_hash = None

    nns_names = []
    for nn_path in [args.names_nn, args.main_text_nn, args.flavor_nn]:
        head, tail_1 = os.path.split(nn_path)
        _, tail_2 = os.path.split(head)
        tail = os.path.join(tail_2, tail_1)
        name = re.sub(r'checkpoint_|\.t7', '', tail)
        nns_names.append(name)

    # resolve and create outdir
    base_count = len(os.listdir(args.outdir))
    args.outdir = os.path.join(args.outdir, f'{base_count:05}_{args.seed}')
    os.makedirs(args.outdir)

    if args.verbosity > 2:
        print(f'operating in {args.outdir}')

    # sample names AI, as a batch
    if args.verbosity > 2:
        print(f'sampling names')

    cards = sample_lstm(nn_path = args.names_nn,
                        seed = args.seed,
                        approx_length_per_chunk = LSTM_LEN_PER_NAME,
                        num_chunks = args.num_cards,
                        parser = functools.partial(encode.AI_to_internal_format, spec='names'),
                        verbosity = args.verbosity)
    # Note that each card in cards will only contain the 'name' field at this point

    # increment seed each card and side for improved uniqueness
    # txt2img uses the seed to directly determine the base noise from which the image is generated
    #   meaning identical seeds produce visually similar images, even given different prompts
    # the LSTM samplers are also a bit biased by the seed, despite being whispered unique names
    seed_diff = 0

    # sample main text and flavor text
    # then render the cards
    for i_card, card in enumerate(cards):
        if args.verbosity > 0:
            print(f'Generating {i_card + 1} / {args.num_cards}')

        # sample main_text AI
        #   which may generate several card sides
        if args.verbosity > 2:
            print(f'sampling main_text')

        card.update(sample_lstm(nn_path = args.main_text_nn,
                                seed = args.seed + seed_diff,
                                approx_length_per_chunk = LSTM_LEN_PER_MAIN_TEXT,
                                num_chunks = 1,
                                parser = functools.partial(encode.AI_to_internal_format, spec='main_text'),
                                whisper_text = f"|1{card['unparsed_name']}|",
                                whisper_every_newline = 1,
                                verbosity = args.verbosity)
        )


        def finish_side(side):
            nonlocal seed_diff

            # sample flavor AI
            if args.verbosity > 12:
                print(f'sampling flavor')

            side.update(sample_lstm(nn_path = args.flavor_nn,
                                    seed = args.seed + seed_diff,
                                    approx_length_per_chunk = LSTM_LEN_PER_FLAVOR,
                                    num_chunks = 1,
                                    parser = functools.partial(encode.AI_to_internal_format, spec='flavor'),
                                    whisper_text = f"{side['unparsed_name']}|",
                                    whisper_every_newline = 1,
                                    verbosity = args.verbosity)
            )

            # add card + generator info text as properties of the card
            # this enables repeatable rendering from the saved card data
            side['set_number'] = base_count
            side['seed'] = args.seed
            side['seed_diff'] = seed_diff
            side['card_number'] = i_card

            side['timestamp'] = timestamp
            side['nns_names'] = nns_names
            side['author'] = args.author
            side['repo_link'] = repo_link
            side['repo_hash'] = repo_hash

            # increment seed_diff for every side
            seed_diff += 1

        finish_side(card)
        if 'b_side' in card: finish_side(card['b_side'])
        if 'c_side' in card: finish_side(card['c_side'])
        if 'd_side' in card: finish_side(card['d_side'])
        if 'e_side' in card: finish_side(card['e_side'])

        if args.verbosity > 2:
            print(f'rendering card')

        render_card(card, args.outdir, args.no_art, args.verbosity)

    # save parsed card data for searchable/parsable reference, search, debugging, etc
    f = open(os.path.join(args.outdir, 'card_data.yaml'), 'w')
    f.write(yaml.dump(cards))
    f.close()

    # TODO statistics over cards


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--names_nn", type=str, help="path to names nn checkpoint, or path to folder with checkpoints (uses longest trained)")
    parser.add_argument("--main_text_nn", type=str, help="path to main_text nn checkpoint, or path to folder with checkpoints (uses longest trained)")
    parser.add_argument("--flavor_nn", type=str, help="path to flavor nn checkpoint, or path to folder with checkpoints (uses longest trained)")
    parser.add_argument("--outdir", type=str, help="path to outdir. Files are saved in a subdirectory based on seed")
    parser.add_argument("--num_cards", type=int, help="number of cards to generate, default 1", default=10)
    parser.add_argument("--seed", type=int, help="if negative or not specified, a random seed is assigned", default=-1)
    parser.add_argument("--no_art", action='store_true', help="disable txt2img render, which occupies most of the generation time. Useful for debugging/testing.")
    parser.add_argument("--author", type=str, default='Novellus Cato', help="author name, displays on card face")
    parser.add_argument("--generate_statistics", action='store_true', help="compute and store statistics over generated cards as yaml file in outdir")
    parser.add_argument("--verbosity", type=int, default=1)
    args = parser.parse_args()

    main(args)

