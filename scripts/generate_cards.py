import argparse
import copy
import json
import math
import os
import pprint
import random
import re
import subprocess

from collections import defaultdict
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


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

MANA_SIZE_MAIN_COST = 78
MANA_SPACING_MAIN_COST = 5
MANA_SIZE_IN_TEXT = 51
MANA_SPACING_IN_TEXT = 3

# fonts assignments are hard to remember
FONT_TITLE = '../image_templates/fonts/beleren-b.ttf'
FONT_MAIN_TEXT = '../image_templates/fonts/mplantin.ttf'
FONT_FLAVOR = '../image_templates/fonts/mplantin-i.ttf'
FONT_MODULAR = '../image_templates/fonts/beleren-bsc.ttf'  # power/toughness, loyalty, mana costs, etc

# defaults, may be overriden at runtime to coerce text fit
DEFAULT_FONT_SIZE_MAIN_COST = 78
DEFAULT_FONT_SIZE_TITLE = 96
DEFAULT_FONT_SIZE_MAIN = 96

TITLE_MAX_HEIGHT = MANA_SIZE_MAIN_COST  # keep these the same height
# max width is computed dynamically, based on size of rendered mana cost

LEFT_TITLE_BOX = 116  # closest text should get to this side
RIGHT_TITLE_BOX_MANA = 1394  # closest mana cost should get to this side
RIGHT_TITLE_BOX_TEXT = 1383  # not fully symmetric since text is squarer than mana costs

HEIGHT_MID_TITLE = 161  # true middle of the image title field
HEIGHT_MID_TITLE_TEXT = HEIGHT_MID_TITLE + 8  # text is rendered slightly off center for a better look

HEIGHT_MID_TYPE = 1416
HEIGHT_MID_TYPE_TEXT = HEIGHT_MID_TYPE + 8  # text is rendered slightly off center for a better look

mana_cost_to_human_readable = {'B': 'black',
                               'C': 'colorless_only',
                               'E': 'energy',
                               'G': 'green',
                               'P': 'phyrexian',
                               'R': 'red',
                               'S': 'snow',
                               'U': 'blue',
                               'W': 'white',
                               'X': 'X',
                               # '\d': 'colorless',  # handled programatically
                              }



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


def parse_flavor(chunk, verbosity):
    s = re.search(r'^.+\|(.+)$', chunk)
    assert s is not None

    flavor = s.group(1)
    return flavor


def parse_mtg_cards(chunk, verbosity):
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

    # create a backlink from the B-side back to the A-side
    # recursive structure is probably not allowed in json, so we do the backlink here
    if 'b_side' in j:
        if 'b_side' in j['b_side']:
            raise ValueError('Nested B-sides are not valid')

        j['b_side']['a_side'] = j

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


def parse_mana_symbols(mana_string):
    # mana_string is eg "{C}{C}{2/W}{B/R}{X}"

    symbols = re.findall(r'(?:\{([^\}]+)\})', mana_string)
    assert symbols is not None
    return list(symbols)


def load_frame_main(card):
    # returns image object for frame

    subdir = '../image_templates/frames/borderless'

    if card['maintypes'] == ['Land']:  # only has the land main-type
        return Image.open(os.path.join(subdir, 'land.png'))

    if card['cost'] is None:
        if 'a_side' in card:
            return load_frame_main(card['a_side'])
        return Image.open(os.path.join(subdir, 'artifact.png'))  # artifact frame is default colorless

    mana_colors_used = set(parse_mana_symbols(card['cost']))

    # these symbols don't contribute to frame selection
    for symbol in ['C', 'E', 'P', 'S', 'X']:
        if symbol in mana_colors_used:
            mana_colors_used.remove(symbol)

    # colorless mana does not contribute to frame selection (its the backup if no colors are present)
    for symbol in copy.deepcopy(mana_colors_used):
        if re.search(r'^\d+$', symbol):
            mana_colors_used.remove(symbol)

    if len(mana_colors_used) == 0:
        return Image.open(os.path.join(subdir, 'artifact.png'))  # artifact frame is default colorless
    elif len(mana_colors_used) == 1:
        return Image.open(os.path.join(subdir, mana_colors_used.pop() + '.png'))  # single colored mana
    else:
        return Image.open(os.path.join(subdir, 'multicolored.png'))


def load_frame(card):
    # TODO support other frame types, determined dynamically (eg planeswalker)
    return load_frame_main(card)


def render_text_largest_fit(text, max_width, max_height, font_path, target_font_size, **kwargs):
    # returns image of rendered text
    #   with the largest font size that renders the given text within max_width and max_height
    #   but not larger than the target_font_size
    # kwargs are passed to ImageDraw.text

    im = Image.new(mode='RGBA', size=(max_width, max_height))
    d = ImageDraw.Draw(im)

    # linear search is inefficient, if this becomes a performance burden, use a bifurcation search
    for font_size in range(target_font_size, 1, -1):
        font = ImageFont.truetype(font_path, size=font_size)

        (left, top, right, bottom) = d.textbbox((0,0), text, font=font, anchor='lt')
        rendered_width = right - left
        rendered_height = bottom - top

        if rendered_width <= max_width and rendered_height <= max_height:
            d.text((0,0), text=text, font=font, anchor='lt', **kwargs)
            im = im.crop((left, top, right, bottom))
            return im

    raise RuntimeError(f'Could not render text "{text}" in given max_width {max_width} and max_height {max_height} using font {font_path} at or below size {target_font_size}')


def render_mana_cost(mana_string, symbol_size, symbol_spacing):
    # TODO support non-square symbols for energy?

    subdir = '../image_templates/modular_elements'

    symbols = parse_mana_symbols(mana_string)

    # stabalize / standardize order
    symbols.sort()  # TODO check sort order for standerdness with colin

    # base image
    width = (symbol_size * len(symbols)) + (symbol_spacing * (len(symbols) - 1))
    im_mana = Image.new(mode='RGBA', size=(width, symbol_size))
    im_mana.putalpha(0)  # full alpha base image

    for i_symbol, symbol in enumerate(symbols):
        # check for colorless mana
        #   which is rendered as text over the mana-circle
        #   no special case for colorless-only mana (nor any other mana), which has one dedicated symbol per cost
        im_symbol = None
        if re.search(r'^\d+$', symbol):
            # acquire and resize the base image
            im_symbol = Image.open(os.path.join(subdir, '0.png'))
            im_symbol = im_symbol.resize((symbol_size, symbol_size))

            # render cost as text over the base image
            #   bound text by max size of a square inscribed into the circular symbol image
            size = math.floor(symbol_size / math.sqrt(2))
            im_text = render_text_largest_fit(symbol, size, size, FONT_MODULAR, DEFAULT_FONT_SIZE_MAIN_COST, fill=(0,0,0,255))
            position = [math.floor(im_symbol.width / 2 - im_text.width / 2),  # center text
                        math.floor(im_symbol.height / 2 - im_text.height / 2)]
            im_symbol.paste(im_text, box=position, mask=im_text)

        else:
            # standardize file name lookup
            symbol = re.sub('/', '', symbol)  # remove the '/'
            symbol = ''.join(sorted(symbol))  # sort subsymbols, if there are multiple

            # acquire and resize the symbol image
            im_symbol = Image.open(os.path.join(subdir, symbol.lower() + '.png'))
            im_symbol = im_symbol.resize((symbol_size, symbol_size))

        # composite the images
        im_mana.paste(im_symbol, (i_symbol * (symbol_size + symbol_spacing), 0), mask=im_symbol)

    return im_mana


def render_card(card_data, art, outdir, verbosity):
    # image sizes and positions are all hard coded magic numbers
    # TODO
    #   main card template
    #       power/toughness graphic
    #           text
    #       main text box (sized together?)
    #           main text
    #               mana costs
    #           flavor
    #       card info
    #           creator
    #           date / seed
    #           link to github
    #   handle planeswalker
    #   handle unique lands

    # art is the lowest layer of the card, but we need a full size image to paste it into
    card = Image.new(mode='RGBA', size=(1500, 2100))

    # resize and crop the art to fit in the frame
    art = art.resize((1550, 1937))
    art = art.crop((25, 0, 1525, 1937))
    card.paste(art, box=(0, 0))

    # add the frame over the art
    frame = load_frame(card_data)
    card.paste(frame, box=(0, 0), mask=frame)

    # TODO add legendary frame overlay

    # main mana cost
    if card_data['cost'] is not None:
        im_mana = render_mana_cost(card_data['cost'], MANA_SIZE_MAIN_COST, MANA_SPACING_MAIN_COST)
        left_main_cost = RIGHT_TITLE_BOX_MANA - im_mana.width
        top_main_cost = HEIGHT_MID_TITLE - im_mana.height // 2
        card.paste(im_mana, box=(left_main_cost, top_main_cost), mask=im_mana)
    else:
        left_main_cost = RIGHT_TITLE_BOX_TEXT  # zero width, adjusted for text spacing constraints

    # name
    max_width = left_main_cost - LEFT_TITLE_BOX - MANA_SPACING_MAIN_COST  # use of MANA_SPACING here is an arbitrary spacer between title and mana cost
    im_text = render_text_largest_fit(card_data['name'], max_width, TITLE_MAX_HEIGHT, FONT_TITLE, DEFAULT_FONT_SIZE_TITLE, fill=(255,255,255,255))
    top = HEIGHT_MID_TITLE_TEXT - im_text.height // 2
    card.paste(im_text, box=(LEFT_TITLE_BOX, top), mask=im_text)

    # type - width constraints are the same as card title
    type_string = ' '.join(card_data['supertypes'] + card_data['maintypes'])
    if card_data['subtypes']:
        type_string += ' - ' + ' '.join(card_data['subtypes'])
    max_width = RIGHT_TITLE_BOX_TEXT - LEFT_TITLE_BOX
    im_text = render_text_largest_fit(type_string, max_width, TITLE_MAX_HEIGHT, FONT_TITLE, DEFAULT_FONT_SIZE_TITLE, fill=(255,255,255,255))
    top = HEIGHT_MID_TYPE_TEXT - im_text.height // 2
    card.paste(im_text, box=(LEFT_TITLE_BOX, top), mask=im_text)

    # TODO rarity

    # clear extra alpha masks from the image pastes
    card.putalpha(255)

    # save image
    base_count = len(os.listdir(outdir))
    out_path = os.path.join(outdir, f"{base_count:05}_{card_data['name']}.png")
    card.save(out_path)


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

    # stabilize processing order
    #   names are guaranteed unique since the sampler deduplicates
    names.sort()

    cards = []  # TODO remove, unecessary. here for the pprint debugging below

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

        im = sample_txt2img(card, args.outdir, args.seed, args.verbosity)

        if args.verbosity > 1:
            print(f'rendering card')

        try:
            render_card(card_data, art, args.outdir, verbosity)
        except e:
            # this should not normally occur
            #   although some cards may have ridiculous stats
            #   which may require extra logic to render
            if verbosity > 0:  
                print('Error while rendering card. Skipping this card')
                print(card_data)
                print(e)

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

