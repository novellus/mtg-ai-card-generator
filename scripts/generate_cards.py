import argparse
import copy
import datetime
import json
import math
import os
import pprint
import random
import re
import shlex
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

# fonts assignments are hard to remember
FONT_TITLE = '../image_templates/fonts/beleren-b.ttf'
FONT_MAIN_TEXT = '../image_templates/fonts/mplantin.ttf'
FONT_FLAVOR = '../image_templates/fonts/mplantin-i.ttf'
FONT_MODULAR = '../image_templates/fonts/beleren-bsc.ttf'  # power/toughness, loyalty, mana costs, etc

DEFAULT_FONT_SIZE = 96  # may be overriden at runtime to coerce text fit

TITLE_MAX_HEIGHT = 94

LEFT_TITLE_BOX = 116  # closest text should get to this side
RIGHT_TITLE_BOX_MANA = 1396  # closest mana cost should get to this side
RIGHT_TITLE_BOX_TEXT = 1383  # not fully symmetric since text is squarer than mana costs

HEIGHT_MID_TITLE = 161  # true middle of the image title field
HEIGHT_MID_TITLE_TEXT = HEIGHT_MID_TITLE + 10  # text is rendered slightly off center for a better look

HEIGHT_MID_TYPE = 1417
HEIGHT_MID_TYPE_TEXT = HEIGHT_MID_TYPE + 9  # text is rendered slightly off center for a better look

TOP_MAIN_TEXT_BOX = 1505
# BOTTOM_MAIN_TEXT_BOX is defined dynamically based on existence of power toughness or loyalty box
LEFT_MAIN_TEXT_BOX = 128
RIGHT_MAIN_TEXT_BOX = 1375

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

    cmd = ( 'python decode.py'
           f' -instring {shlex.quote(chunk)}'
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


def parse_mana_symbols(mana_string, None_acceptable=False):
    # mana_string is eg "{C}{C}{2/W}{B/R}{X}"

    symbols = re.findall(r'(?:\{([^\}]+)\})', mana_string)
    symbols = list(symbols) or None  # convert empty list to None to raise errors on inappropriate usage
    if not None_acceptable:
        assert symbols is not None
    return symbols


def load_frame(card):
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


def render_text_largest_fit(text, max_width, max_height, font_path, target_font_size, crop_final=True, **kwargs):
    # returns image of rendered text
    #   with the largest font size that renders the given text within max_width and max_height
    #   but not larger than the target_font_size
    # kwargs are passed to ImageDraw.text
    # if crop_final, the image is cropped to its non-zero bounding box before checking constraints

    # linear search is inefficient, if this becomes a performance burden, use a bifurcation search
    for font_size in range(target_font_size, 1, -1):
        try:
            im, _ = render_complex_text(text, max_width, font_path, font_size, **kwargs)
        except FontTooLargeError:
            continue

        if crop_final:
            im = im.crop(im.getbbox())

        if im.height <= max_height:
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
    im_mana = Image.new(mode='RGBA', size=(width, symbol_size), color=(0, 0, 0, 0))

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
            im_text = render_text_largest_fit(symbol, size, size, FONT_MODULAR, symbol_size, fill=(0,0,0,255))
            position = (math.floor(im_symbol.width / 2 - im_text.width / 2),  # center text
                        math.floor(im_symbol.height / 2 - im_text.height / 2))
            im_symbol.alpha_composite(im_text, dest=position)

        else:
            # standardize file name lookup
            symbol = re.sub('/', '', symbol)  # remove the '/'
            symbol = ''.join(sorted(symbol))  # sort subsymbols, if there are multiple

            # acquire and resize the symbol image
            im_symbol = Image.open(os.path.join(subdir, symbol.lower() + '.png'))
            im_symbol = im_symbol.resize((symbol_size, symbol_size))

        # composite the images
        im_mana.alpha_composite(im_symbol, dest=(i_symbol * (symbol_size + symbol_spacing), 0))

    return im_mana


def load_power_toughness_overlay(card):
    # returns image object for power / toughness overlay image
    # which image we load depends on card details

    subdir = '../image_templates/modular_elements'

    if card['cost'] is None:
        if 'a_side' in card:
            return load_power_toughness_overlay(card['a_side'])
        return Image.open(os.path.join(subdir, 'pt_colorless.png'))

    mana_colors_used = set(parse_mana_symbols(card['cost']))

    # these symbols don't contribute to selection
    for symbol in ['C', 'E', 'P', 'S', 'X']:
        if symbol in mana_colors_used:
            mana_colors_used.remove(symbol)

    # colorless mana does not contribute to selection (its the backup if no colors are present)
    for symbol in copy.deepcopy(mana_colors_used):
        if re.search(r'^\d+$', symbol):
            mana_colors_used.remove(symbol)

    if len(mana_colors_used) == 0:
        if 'Artifact' in card['maintypes']:
            return Image.open(os.path.join(subdir, 'pt_artifact.png'))
        elif 'Vehicle' in card['subtypes']:
            return Image.open(os.path.join(subdir, 'pt_vehicle.png'))
        else:
            return Image.open(os.path.join(subdir, 'pt_colorless.png'))
    elif len(mana_colors_used) == 1:
        return Image.open(os.path.join(subdir, 'pt_' + mana_colors_used.pop() + '.png'))  # single colored mana
    else:
        return Image.open(os.path.join(subdir, 'pt_multicolored.png'))


def load_set_symbol(card):
    # returns image object for power / toughness overlay image
    # which image we load depends on card details

    subdir = '../image_templates/set_symbols'

    f_name = re.sub(' ', '_', card['rarity'])
    return Image.open(os.path.join(subdir, f'{f_name}.png'))


class FontTooLargeError(Exception):
    # raised to indicate the given operation with constraints is impossible
    # ie that a single character at the specified font size violates the maximum width constraint
    pass


def symbol_sizing(font_size):
    # size vertical kerning and symbols together
    #   so that we don't get really small text with large whitespace gaps from inline symbology
    vertical_kerning = math.ceil(font_size * 1.1)
    symbol_size = math.ceil(font_size * 0.8125)
    symbol_spacing = math.ceil(symbol_size * 0.064)

    return vertical_kerning, symbol_size, symbol_spacing


def render_complex_text(text, max_width, font_path, font_size, long_token_mode=False, **kwargs):
    # renders multiline text with inline symbols at given font size under max_width constraint
    #   newlines are inserted at optimal locations anywhere there is whitespace
    #       or in the middle of a word (delimited by whitespace) if and only if the word by itself exceeds the max_width constraint
    #   honors newlines in the input text, forcing a newline at those locations, regardless of optimal spacing
    #   inline symbols are sized and spaced appropriate to the font size
    # Note that all consecutive whitespace other than newlines will be dissolved into a single space regardless of type
    # returns rendered image and boolean
    #   boolean indicates whether any words were broken up into multiple lines
    # long_token_mode changes the following behaviors, and should probably only be used for recursion
    #   text is only one overly long word
    #   spaces are omitted during token recombination to form lines
    #   returns list of rendered lines (and no boolean), instead of one rendered image
    # TODO support planeswalker symbology

    assert max_width > 0
    assert font_size > 0
    assert font_path

    if long_token_mode and len(text) == 1:
        raise FontTooLargeError(f'{text}, {max_width}, {font_path}, {font_size}, {long_token_mode}, {kwargs}')

    vertical_kerning, symbol_size, symbol_spacing = symbol_sizing(font_size)
    optional_space = '' if long_token_mode else ' '

    def token_encodes_symbols(token):
        return parse_mana_symbols(token, None_acceptable=True) is not None

    # break text into words, symbols, and newline characters
    #   which will be partitioned into rendered lines
    #   rendered lines will then be added together to form a rendered multiline text
    tokens = None
    if not long_token_mode:
        text = text.strip()
        tokens = re.findall(r'(\n|[^\s]+)', text)
        # alternatively break up symbol groups by default, but I probably don't want that
        # tokens = re.findall(r'(\n|\{[^\}]+\}|[^\s]+)', text)
    else:
        if token_encodes_symbols(text):
            tokens = re.findall(r'(\{[^\}]+\})', text)  # individual symbols
        else:
            tokens = list(text)  # individual characters
        assert len(tokens) > 1  # prevent infinite recursion. We should never get here unless something is malformatted

    # construct test image for rendering size tests, but not for final text rendering
    im_test = Image.new(mode='RGBA', size=(1, 1))  # size is irrelevant
    d_test = ImageDraw.Draw(im_test)
    font = ImageFont.truetype(font_path, size=font_size)

    def render_text(t):
        # check size, and then render on a minimally sized image
        (left, top, right, bottom) = d_test.textbbox((0,0), t, font=font, anchor='lt')
        rendered_width = right - left
        rendered_height = bottom - top
        im = Image.new(mode='RGBA', size=(rendered_width, rendered_height))
        d = ImageDraw.Draw(im)
        d.text((0,0), text=t, font=font, anchor='lt', **kwargs)
        return im

    def render_line(l):
        width = sum([x.width for x in l])
        width += symbol_spacing * (len(l) - 1)
        height = max([x.height for x in l])  # these should all be very close in height
        line = Image.new(mode='RGBA', size=(width, height))
        horizontal_pos = 0
        for im in l:
            position = (horizontal_pos,
                        math.floor(line.height / 2 - im.height / 2))  # vertically center image
            line.alpha_composite(im, dest=position)
            horizontal_pos += im.width + symbol_spacing
        return line

    def render_all_pending(render_None=False):
        line_was_rendered = False
        nonlocal rendered_lines
        nonlocal line_images
        nonlocal consolidated_words

        # render any pending text and add it to the line
        if consolidated_words:
            line_images.append(render_text(consolidated_words))
            consolidated_words = ''

        # render any pending line images
        if line_images:
            rendered_lines.append(render_line(line_images))
            line_images = []
            line_was_rendered = True
        elif render_None:
            rendered_lines.append(None)  # None indicates empty line (no image)

        return line_was_rendered

    rendered_lines = []
    line_images = []
    consolidated_words = ''
    broken_token = False
    # render line of text, adding one word at a time, until max_width constraint violation
    while tokens:
        token = tokens[0]
        token_adds = None
        cached_mana_render = None

        # try adding one token to the line, then check constraints
        if token == '\n':
            render_all_pending(render_None=True)

            # nothing further to compute for newlines
            tokens.pop(0)
            continue

        elif token_encodes_symbols(token):
            # render any pending text and add it to the line now
            # but don't render the line incase this token still fits
            if consolidated_words:
                line_images.append(render_text(consolidated_words))
                consolidated_words = ''

            cached_mana_render = render_mana_cost(token, symbol_size, symbol_spacing)
            token_adds = cached_mana_render.width

        else:
            # consolidate consecutive text into one text render so we don't have to deal with horizontal kerning
            token_text = None
            if consolidated_words:
                token_text = consolidated_words + optional_space + token
            else:
                token_text = token
            (left, top, right, bottom) = d_test.textbbox((0,0), token_text, font=font, anchor='lt')
            rendered_width = right - left
            token_adds = rendered_width

        if line_images:
            token_adds += symbol_spacing

        composite_line_width = sum([x.width for x in line_images])
        composite_line_width += symbol_spacing * (len(line_images) - 1)
        composite_line_width += token_adds

        # check constraints
        if composite_line_width > max_width:
            # line is at max dimensions, so render final line image, not including the current offending token
            line_was_rendered = render_all_pending()

            # if nothing was rendered, then nothing was pending
            # handle tokens which when rendered by themselves already exceed max_width
            # break these tokens up to fit
            if not line_was_rendered:
                lines = render_complex_text(token, max_width, font_path, font_size, long_token_mode=True, **kwargs)
                for line in lines[:-1]:
                    rendered_lines.append(line)
                # the last rendered line could have room for more stuff
                line_images.append(lines[-1])
                broken_token = True
                tokens.pop(0)

        else:  # token fits on line
            if token_encodes_symbols(token):
                line_images.append(cached_mana_render)
            else:
                if consolidated_words:
                    consolidated_words += optional_space
                consolidated_words += token
            tokens.pop(0)

    # render any pending text or line images at the end of token list
    render_all_pending()

    if long_token_mode:
        # don't composite the multiline image yet
        return rendered_lines

    # finally, render all lines together
    height = vertical_kerning * len(rendered_lines)
    width = max([x.width for x in rendered_lines])
    multiline = Image.new(mode='RGBA', size=(width, height))
    for i_im, im in enumerate(rendered_lines):
        if im is not None:  # None => blank line
            multiline.alpha_composite(im, dest=(0, i_im * vertical_kerning))

    return multiline, broken_token


def render_loyalty_modifier(mod_text, height):
    loyalty_value = int(mod_text)
    im_loyalty_mod = None
    if loyalty_value == 0:
        im_loyalty_mod = Image.open('../image_templates/modular_elements/+0.png')
        im_text = render_text_largest_fit(mod_text, 155, 71, FONT_MODULAR, 100, fill=(255,255,255,255))
        position = (math.floor(124 - im_text.width / 2),
                    math.floor(80 - im_text.height / 2))
        im_loyalty_mod.alpha_composite(im_text, dest=position)
        im_text = render_text_largest_fit(':', 35, 71, FONT_MODULAR, 100, fill=(255,255,255,255))
        position = (math.floor(261 - im_text.width / 2),
                    math.floor(80 - im_text.height / 2))
        im_loyalty_mod.alpha_composite(im_text, dest=position)
    elif loyalty_value > 0:
        im_loyalty_mod = Image.open('../image_templates/modular_elements/+.png')
        im_text = render_text_largest_fit(mod_text, 155, 71, FONT_MODULAR, 100, fill=(255,255,255,255))
        position = (math.floor(124 - im_text.width / 2),
                    math.floor(102 - im_text.height / 2))
        im_loyalty_mod.alpha_composite(im_text, dest=position)
        im_text = render_text_largest_fit(':', 35, 71, FONT_MODULAR, 100, fill=(255,255,255,255))
        position = (math.floor(261 - im_text.width / 2),
                    math.floor(102 - im_text.height / 2))
        im_loyalty_mod.alpha_composite(im_text, dest=position)
    else:
        im_loyalty_mod = Image.open('../image_templates/modular_elements/-.png')
        im_text = render_text_largest_fit(mod_text, 155, 71, FONT_MODULAR, 100, fill=(255,255,255,255))
        position = (math.floor(124 - im_text.width / 2),
                    math.floor(64 - im_text.height / 2))
        im_loyalty_mod.alpha_composite(im_text, dest=position)
        im_text = render_text_largest_fit(':', 35, 71, FONT_MODULAR, 100, fill=(255,255,255,255))
        position = (math.floor(261 - im_text.width / 2),
                    math.floor(64 - im_text.height / 2))
        im_loyalty_mod.alpha_composite(im_text, dest=position)

    size = (math.ceil(height / im_loyalty_mod.height * im_loyalty_mod.width),
                      height)
    im_loyalty_mod = im_loyalty_mod.resize(size)

    return im_loyalty_mod


def render_main_text_box(card):
    # returns image of main text box including these fields
    #   main text with inline symbols
    #   field separator
    #   flavor text
    # and
    #   with optimally located linebreaks
    #   with the largest font size that renders the given text within max_width and max_height
    #   but not larger than the DEFAULT_FONT_SIZE
    # separate from render_text_largest_fit since multiple fields need to be optimized together

    # size main text box
    # dynamically shorten main text if one of these is rendered
    if card['loyalty']:
        bottom_main_text_box = 1840
    elif card['power_toughness']:
        bottom_main_text_box = 1858
    else:
        bottom_main_text_box = 1923

    width = RIGHT_MAIN_TEXT_BOX - LEFT_MAIN_TEXT_BOX
    max_height = bottom_main_text_box - TOP_MAIN_TEXT_BOX
    sep_bar = Image.open('../image_templates/modular_elements/whitebar.png')
    # TODO Refine this cropping / sizing
    sep_bar = sep_bar.resize((math.ceil(width * 1.05), 6))  # auto-crop some of the more faded edges

    # prefer smaller fonts to broken tokens, unless font needs to be lowered below criterion
    largest_rendered_with_broken_token = None
    max_font_point_loss_to_unbreak_token = 10

    # parse main text for loyalty modifier symbols
    # partition main text if these are found
    # if these are not found, partitioned_main_text will be a list with only one element
    partitioned_main_text = []  # list of [str-encoded loyalty +/- number, text to the right of the loyalty +/- icon]
    tokens = re.split(r'\[([+-]?\d+)\]:\s*', card['main_text'])

    if tokens[0] != '':
        sub_tokens = [None, tokens[0]]
        partitioned_main_text.append(sub_tokens)

    for i in range(1, len(tokens), 2):  # re.split guarantees odd indeces are the captured group
        sub_tokens = [tokens[i], tokens[i+1]]
        partitioned_main_text.append(sub_tokens)

    # search over the font_size space until constraints are met
    # linear search is inefficient, if this becomes a performance burden, use a bifurcation search
    for font_size in range(DEFAULT_FONT_SIZE, 1, -1):
        broken_token = False
        im_main_texts = []

        # size loyalty modifier icons
        vertical_kerning, symbol_size, symbol_spacing = symbol_sizing(font_size)
        loyalty_height = math.ceil(3 * symbol_size)
        loyalty_spacing_horizontal = math.ceil(3 * symbol_spacing)
        loyalty_spacing_vertical = math.ceil(0.5 * vertical_kerning)

        # the first partitioned element may not have any loyalty modifier preceeding it
        #   and indeed may be the only element in the list, if there are no encoded loyalty modifers
        if partitioned_main_text[0][0] is None:
            im, _broken_token = render_complex_text(partitioned_main_text[0][1], width, FONT_MAIN_TEXT, font_size, fill=(255,255,255,255))
            im = im.crop(im.getbbox())
            im_main_texts.append(im)
            broken_token = broken_token or _broken_token

        # now render all loyalty icons, and render partitioned main text lines to the right of them
        for mod_text, main_text in partitioned_main_text:
            if mod_text is not None:
                # render the loyalty modifer
                im_loyalty_mod = render_loyalty_modifier(mod_text, loyalty_height)

                # render the text
                sub_width = width - im_loyalty_mod.width - loyalty_spacing_horizontal
                im_text, _broken_token = render_complex_text(main_text, sub_width, FONT_MAIN_TEXT, font_size, fill=(255,255,255,255))
                im_text = im_text.crop(im_text.getbbox())
                broken_token = broken_token or _broken_token

                # composite both images
                size = (im_loyalty_mod.width + loyalty_spacing_horizontal + im_text.width,
                        max(im_loyalty_mod.height, im_text.height))
                im = Image.new(mode='RGBA', size=size, color=(0, 0, 0, 0))
                im.alpha_composite(im_loyalty_mod, dest=(0,0))
                height = 0
                if im_text.height < im_loyalty_mod.height:
                    height = math.floor(im_loyalty_mod.height / 2 - im_text.height / 2)
                im.alpha_composite(im_text, dest=(im_loyalty_mod.width + loyalty_spacing_horizontal, height))

                im_main_texts.append(im)

        # render the flavor text
        im_flavor, _broken_token = render_complex_text(card['flavor'], width, FONT_FLAVOR, font_size, fill=(255,255,255,255))
        im_flavor = im_flavor.crop(im_flavor.getbbox())
        broken_token = broken_token or _broken_token

        height_sep_bar = math.floor(font_size *2/3)
        height_sep_bar = max(height_sep_bar, sep_bar.height * 3)  # but no smaller than the actual graphic + margin

        composite_height = sum([x.height for x in im_main_texts])
        composite_height += loyalty_spacing_vertical * (len(im_main_texts) - 1)
        composite_height += height_sep_bar + im_flavor.height

        if composite_height <= max_height:
            # composite all the main-text-box images together
            im = Image.new(mode='RGBA', size=(width, composite_height), color=(0, 0, 0, 0))

            height = 0
            for im_main_text in im_main_texts:
                im.alpha_composite(im_main_text, dest=(0, height))
                height += im_main_text.height + loyalty_spacing_vertical
            height_main_text = height - loyalty_spacing_vertical  # spacing after the main text is handled by the sep bar

            pos = (math.floor(width / 2 - sep_bar.width / 2),  # horizontally center
                   math.floor(height_main_text + height_sep_bar / 2 - sep_bar.height / 2))  # centered between main text and flavor fields
            im.alpha_composite(sep_bar, dest=pos)
            im.alpha_composite(im_flavor, dest=(0, height_main_text + height_sep_bar))

            # return either this render, or a larger render with a broken token if it exists and meets criteria
            # store broken token renders until we find an unbroken size to compare, or run out of search space
            if broken_token and largest_rendered_with_broken_token is None:
                largest_rendered_with_broken_token = (im, font_size)
            else:
                if (largest_rendered_with_broken_token is not None
                    and largest_rendered_with_broken_token[1] - font_size <= max_font_point_loss_to_unbreak_token):
                    return largest_rendered_with_broken_token[0]
                return im

    # if we can only render with a broken token, then do so
    if largest_rendered_with_broken_token is not None:
        return largest_rendered_with_broken_token[0]

    raise RuntimeError(f'Could not render text "{text}" in given max_width {max_width} and max_height {max_height} using font {font_path} at or below size {target_font_size}')


def render_card(card_data, art, outdir, verbosity, set_count, seed, art_seed_diff, timestamp, nns_names, base_count=None):
    # image sizes and positions are all hard coded magic numbers

    # used for rendering b-sides at the same base_count
    base_count = base_count or len(os.listdir(outdir))

    # art is the lowest layer of the card, but we need a full size image to paste it into
    card = Image.new(mode='RGBA', size=(1500, 2100))

    # resize and crop the art to fit in the frame
    art = art.resize((1550, 1937))
    art = art.crop((25, 0, 1525, 1937))
    card.paste(art, box=(0, 0))

    # add the frame over the art
    frame = load_frame(card_data)
    card.alpha_composite(frame, dest=(0, 0))

    # TODO add legendary frame overlay

    # main mana cost
    if card_data['cost'] is not None:
        max_width = (RIGHT_TITLE_BOX_MANA - LEFT_TITLE_BOX) // 2
        im_mana = render_text_largest_fit(card_data['cost'], max_width, TITLE_MAX_HEIGHT, FONT_TITLE, 120)
        left_main_cost = RIGHT_TITLE_BOX_MANA - im_mana.width
        top_main_cost = HEIGHT_MID_TITLE - im_mana.height // 2
        card.alpha_composite(im_mana, dest=(left_main_cost, top_main_cost))
    else:
        left_main_cost = RIGHT_TITLE_BOX_TEXT  # zero width, adjusted for text spacing constraints

    # name
    # specifically don't crop title boxes, so that the text baseline is always in the same location
    #   ie the text doesn't shift around depending on whether it contains tall characters dropping below the baseline
    #   which would cause it to appear off center
    max_width = left_main_cost - LEFT_TITLE_BOX - 5
    im_text = render_text_largest_fit(card_data['name'], max_width, TITLE_MAX_HEIGHT, FONT_TITLE, DEFAULT_FONT_SIZE, crop_final=False, fill=(255,255,255,255))
    top = HEIGHT_MID_TITLE_TEXT - im_text.height // 2
    card.alpha_composite(im_text, dest=(LEFT_TITLE_BOX, top))

    # set symbol
    im_set = load_set_symbol(card_data)
    im_set = im_set.resize((97, 97))
    pos = (RIGHT_TITLE_BOX_MANA - im_set.width,
           HEIGHT_MID_TYPE - im_set.height // 2)
    card.alpha_composite(im_set, dest=pos)
    left_set = pos[0]

    # type - width constraints are almost the same as card title
    type_string = ' '.join(card_data['supertypes'] + card_data['maintypes'])
    if card_data['subtypes']:
        type_string += ' - ' + ' '.join(card_data['subtypes'])
    max_width = left_set - LEFT_TITLE_BOX - 5  # 5 is arbitrary spacing
    im_text = render_text_largest_fit(type_string, max_width, TITLE_MAX_HEIGHT, FONT_TITLE, DEFAULT_FONT_SIZE, crop_final=False, fill=(255,255,255,255))
    top = HEIGHT_MID_TYPE_TEXT - im_text.height // 2
    card.alpha_composite(im_text, dest=(LEFT_TITLE_BOX, top))

    # power toughness
    #   first render the infobox overlay
    #   then render text on top of that
    if card_data['power_toughness'] is not None:
        im_pt = load_power_toughness_overlay(card_data)
        card.alpha_composite(im_pt, dest=(1137, 1858))  # magic numbers, image has assymetric partial alpha around the edges

        pt_string = '/'.join([str(x) for x in card_data['power_toughness']])
        im_text = render_text_largest_fit(pt_string, 194, 82, FONT_MODULAR, DEFAULT_FONT_SIZE, fill=(0,0,0,255))
        top = 1928 - im_text.height // 2
        left = 1292 - im_text.width // 2
        card.alpha_composite(im_text, dest=(left, top))

    # loyalty
    if card_data['loyalty'] is not None:
        im_loyalty = Image.open('../image_templates/modular_elements/loyalty.png')
        card.alpha_composite(im_loyalty, dest=(1200, 1847))

        im_text = render_text_largest_fit(str(card_data['loyalty']), 154, 60, FONT_MODULAR, DEFAULT_FONT_SIZE, fill=(255,255,255,255))
        top = 1915 - im_text.height // 2
        left = 1314 - im_text.width // 2
        card.alpha_composite(im_text, dest=(left, top))

    # main text box
    im_main_text_box = render_main_text_box(card_data)
    card.alpha_composite(im_main_text_box, dest=(LEFT_MAIN_TEXT_BOX, TOP_MAIN_TEXT_BOX))

    # info text
    side_id = None
    if 'b_side' in card_data:
        side_id = '-A'
    elif 'a_side' in card_data:
        side_id = '-B'

    _nns_names = []
    for nn_path in nns_names:
        head, tail_1 = os.path.split(nn_path)
        _, tail_2 = os.path.split(head)
        tail = os.path.join(tail_2, tail_1)
        name = re.sub(r'checkpoint_|\.t7', '', tail)
        _nns_names.append(name)
    nn_names = ', '.join(_nns_names)

    d = ImageDraw.Draw(card)
    font = ImageFont.truetype(FONT_TITLE, size=35)
    card_id = f'ID: {set_count:05}_{seed}+{art_seed_diff}_{base_count:05}{side_id or ""}'
    author = 'Novellus Cato'
    repo_link = 'https://github.com/novellus/mtg-ai-card-generator'
    d.text((100, 1971), text=card_id, font=font, anchor='lt', fill=(255,255,255,255))
    d.text((1166, 1971), text=timestamp, font=font, anchor='rt', fill=(255,255,255,255))

    im_nn_names = render_text_largest_fit(nn_names, 1299, 35, FONT_TITLE, 35, fill=(255,255,255,255))
    card.alpha_composite(im_nn_names, dest=(100, 2020 - im_nn_names.height // 2))

    im_brush = Image.open('../image_templates/modular_elements/artistbrush.png')
    im_brush = im_brush.resize((40, 25))
    card.alpha_composite(im_brush, dest=(100, 2043 + 2))
    d.text((145, 2043), text=author, font=font, anchor='lt', fill=(255,255,255,255))
    d.text((1399, 2043), text=repo_link, font=font, anchor='rt', fill=(255,255,255,255))

    # save image
    # the space in f_name is important for parsability
    #   because the name is guaranteed to not start with a space
    #   while it could (legally) start with "-A"
    f_name = f"{base_count:05}{side_id or ''} {card_data['name']}"
    out_path = os.path.join(outdir, f"{f_name}.png")
    card.save(out_path)

    return base_count


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

    timestamp = datetime.datetime.utcnow().isoformat(sep=' ', timespec='seconds')

    # resolve folders to checkpoints
    args.names_nn = resolve_folder_to_checkpoint_path(args.names_nn)
    args.main_text_nn = resolve_folder_to_checkpoint_path(args.main_text_nn)
    args.flavor_nn = resolve_folder_to_checkpoint_path(args.flavor_nn)
    nns_names = [args.names_nn, args.main_text_nn, args.flavor_nn]

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

    cards = []

    # increment art seed each iteration for more unique images
    # lstm samplers don't need this because they are seeded with a unique name
    #   which creates a unique character probability distribution for the next character
    #   and then the torch library uses the single stock seed to sample the next character from that distribution
    #   which is still a net unique decision
    # whereas the txt2img uses the seed to directly determine the base noise from which the image is generated
    #   meaning identical seeds produce visually similar images, even given different prompts
    art_seed_diff = 0

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

        def finish_card(card, card_num=None):
            nonlocal art_seed_diff

            if args.verbosity > 1:
                print(f'sampling flavor')

            flavors = sample_lstm(nn_path = args.flavor_nn,
                                  seed = args.seed,
                                  approx_length_per_chunk = LSTM_LEN_PER_FLAVOR,
                                  num_chunks = 1,
                                  delimiter = '\n',
                                  parser=parse_flavor,
                                  whisper_text = f"{card['name']}|",
                                  whisper_every_newline = 1,
                                  verbosity = args.verbosity)
            card['flavor'] = flavors[0]

            if args.verbosity > 1:
                print(f'sampling txt2img')

            art = sample_txt2img(card, args.outdir, args.seed + art_seed_diff, args.verbosity)

            if args.verbosity > 1:
                print(f'rendering card')

            card_num = render_card(card, art, args.outdir, args.verbosity, base_count, args.seed, art_seed_diff, timestamp, nns_names, card_num)
            art_seed_diff += 1

        card_num = finish_card(card)
        if 'b_side' in card:
            # render B-side at same card_num to ID side associations
            # card_num becomes the first element of the file name, and is printed on the card face
            finish_card(card['b_side'], card_num)

        cards.append(card)

    # TODO statistics over cards
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

