import base58
import base64
import copy
import io
import math
import os
import pprint
import re
import requests
import signal
import subprocess
import sys
import time

import mtg_constants

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import PngImagePlugin


# Constants
ADDRESS_A1SD = 'http://127.0.0.1:7860'
PATH_A1SD = '../A1SD'


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


def handle_sigint(signum, frame):
    # gracefull kill the A1SD server before exiting
    terminate_A1SD_server(float('inf'))  # use infinite verbosity, since user ctrl+c'd
    sys.exit(0)
signal.signal(signal.SIGINT, handle_sigint)


def A1SD_server_up(verbosity):
    # make an arbitrary API call toe check if the server is up
    # we make this check instead of checking PROCESS_A1SD object incase
    #   the server has failed, started with incorrect arguments, code error, server was started outside of this program, etc

    try:
        requests.get(f'{ADDRESS_A1SD}/sdapi/v1/embeddings')
        if verbosity > 2:
            print('A1SD server is up')
        return True
    except requests.exceptions.ConnectionError:
        if verbosity > 2:
            print('A1SD server is not up')
        return False


PROCESS_A1SD = None  # keep this around so the process can be killed on exit
def start_A1SD_server(verbosity):
    # starts server and waits for it to be ready before returning

    global PROCESS_A1SD
    if PROCESS_A1SD is not None:
        raise RuntimeError(f'A1SD server should already be running?\n\tPID: {PROCESS_A1SD.pid}\n\tpoll: {PROCESS_A1SD.poll()}')

    if verbosity > 1:
        print('Starting A1SD server')

    PROCESS_A1SD = subprocess.Popen('bash webui.sh',
                                    shell=True,
                                    bufsize=1,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    encoding='utf-8',
                                    start_new_session=True,  # enables killing all spawned processes as a group
                                    cwd=PATH_A1SD)

    # wait for the server to startup to a ready state
    #   check for server to print its ready state to console
    # check server response using a non-blocking-read workaround
    #   this would be much easier if there was a supported simple interface to communicate with ongoing processes
    #   such as that implemented by threading - use a pipe, poll the pipe for data, read pipe data
    # however, the subprocess module doesn't provide anything so nice for ongoing processes
    #   docs suggest using Popen.communicate, but this doesn't support our use case since it waits for the process to finish, or raises a TimeoutExpired exception
    #   blindly calling Popen.stdout.read() or .readline() will cause hangs, since these both wait for a certain code to be written to stream before returning
    # so instead, we're gonna modify the file stream provided by Popen to implement a non-blocking read mechanism
    #   this causes the read() calls to always return, or throw an unhelpful TypeError if the stream is empty
    #   while readline() will just return an empty string when the stream is empty
    #   empty stream behavior plus line buffering makes readline the obvious preference here
    # Finally, the stream has no way to tell if it has data, so just read one line at a time at fixed frequency
    os.set_blocking(PROCESS_A1SD.stdout.fileno(), False)

    startup_timeout = 60  # seconds
    poll_frequency = 10  # Hz
    for i in range(startup_timeout * poll_frequency):
        time.sleep(1 / poll_frequency)
        line = PROCESS_A1SD.stdout.readline()
        if re.search('Running on local URL', line):
            break
    else:
        raise RuntimeError(f'A1SD server startup timed-out\n\tPID: {PROCESS_A1SD.pid}\n\tpoll: {PROCESS_A1SD.poll()}')

    assert A1SD_server_up(verbosity)


def terminate_A1SD_server(verbosity):
    if PROCESS_A1SD is not None:
        if verbosity > 1:
            print('Terminating A1SD server')

        # cannot use Popen.terminate() or kill() because they will not kill further spawned processes, especially the process responsible for consuming vram
        os.killpg(os.getpgid(PROCESS_A1SD.pid), signal.SIGTERM)
        PROCESS_A1SD.communicate(timeout=10)  # clears pipe buffers, and waits for process to close


def sample_txt2img(card, cache_path, seed, verbosity):
    # start stable-diffusion web server if its not already up
    if not A1SD_server_up(verbosity):
        start_A1SD_server(verbosity)

    # remove cached file if it already exists
    if os.path.exists(cache_path):
        os.remove(cache_path)
        if verbosity > 2:
            print(f'overwriting image file at {cache_path}')
    else:
        if verbosity > 2:
            print(f'caching image file to {cache_path}')

    # execute txt2img
    # see f'{ADDRESS_A1SD}/docs' for API description
    #   its outdated, and not all the listed APIs work, but still the best reference I have

    payload = {
        'prompt': f"{card['name']}, high fantasy",

        # try to dissuade the AI from generating images of MTG cards, which adds confusing and undesired text/symbols/frame elements
        #   its not foolproof, and in practice ~10% make it through anyway, but that's better than 100% without this dissuasion
        #   There's probably several better ways to approach this?
        #   the mtgframe* keywords are embeddings, see https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#textual-inversion
        'negative_prompt': 'mtgframe5, mtgframe6, mtgframe7, mtgframe8, mtgframe10, mtgframe11, blurry, text',

        'steps': 20,
        'batch_size': 1,
        'n_iter': 1,
        'width': 512,
        'height': 512,
        'sampler_index': 'Euler',  # also available: 'sampler_name'... ?
        'seed': seed,

        # render the image orignally at 512x512 since the AI artifacts heavily at any other resolution
        # then use another AI (LDSR) to upscale to 1024x1024
        # 'enable_hr': True,
        # 'hr_scale': 2,
        # 'hr_upscaler': 'LDSR',
        # 'denoising_strength': 0.683,  # empirical, subjective, heavily affects quality
    }

    # decode the response
    #   we asked a batch processor for a single sample
    #   image data is base64 ascii-encoded
    response = requests.post(f'{ADDRESS_A1SD}/sdapi/v1/txt2img', json=payload)
    assert response.status_code != 500, f'500 status code: frequently means out of memory error\n{time.sleep(1) or ""}{"".join(PROCESS_A1SD.stdout.readlines())}'

    response = response.json()
    image_data = response['images'][0]
    im = Image.open(io.BytesIO(base64.b64decode(image_data)))

    # request png info blob from the server
    #   which gives us enough information about the generated image to regenerate it
    #   ie: all txt2img input parameters, including those which have default values and are not specified here
    # This info blob will be saved as part of the image data
    #   and is in a format which the AUTOMATIC1111 web server understands, so we're not gonna add random whatevers to it
    response = requests.post(f'{ADDRESS_A1SD}/sdapi/v1/png-info', json={"image": "data:image/png;base64," + image_data})
    png_info = response.json()['info']

    # cache image
    encoded_info = PngImagePlugin.PngInfo()
    encoded_info.add_text("parameters", png_info)  # 'parameters' key is looked for by AUTOMATIC1111 web server
    im.save(cache_path, pnginfo=encoded_info)

    return im, png_info


def parse_mana_symbols(mana_string, None_acceptable=False):
    # mana_string is eg "{C}{C}{2/W}{B/R}{X}"

    symbols = re.findall(r'(?:\{([^\}]+)\})', mana_string)
    symbols = list(symbols) or None  # convert empty list to None to raise errors on inappropriate usage
    if not None_acceptable:
        assert symbols is not None
    return symbols


def colors_used(s):
    # returns set of colors used in mana cost string s
    # returns one of
    #   set of str of color names (eg {'Red', 'Blue'})
    #   'Colorless', if there are symbols in s, but none of them are colored
    #   None, if there are no symbols in s, or s is None

    if s is None:
        return None

    colors = set()
    found_colorless = False
    for sym in parse_mana_symbols(s):
        new_colors = mtg_constants.mtg_symbol_color(sym)
        if new_colors == 'Colorless':
            found_colorless = True
        else:
            colors.update(new_colors)

    colors = colors or None
    if found_colorless:
        colors = colors or 'Colorless'

    return colors


def load_frame(card):
    # returns image object for frame

    subdir = '../image_templates/frames/borderless'

    if card['type'] == 'Land':  # only has the land main-type
        return Image.open(os.path.join(subdir, 'land.png'))

    if card['cost'] is None:
        if 'a_side' in card:
            return load_frame_main(card['a_side'])
        return Image.open(os.path.join(subdir, 'artifact.png'))  # artifact frame is default colorless

    mana_colors_used = colors_used(card['cost'])

    if mana_colors_used == 'Colorless':
        return Image.open(os.path.join(subdir, 'artifact.png'))  # artifact frame is default colorless
    elif len(mana_colors_used) == 1:
        f_name = {'Black':'B', 'Green':'G', 'Red':'R', 'Blue':'U', 'White':'W'}[mana_colors_used.pop()]
        return Image.open(os.path.join(subdir, f_name + '.png'))  # single colored mana
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
    subdir = '../image_templates/modular_elements'

    symbols = parse_mana_symbols(mana_string)

    # stabalize / standardize symbol order
    # proper mana order is outlined here https://cardboardkeeper.com/mtg-color-order/
    # but the system outlined is complicated and difficult to implement, for trivial gains
    # so we're gonna ignore that and just sort the damn list for stability
    symbols.sort()

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

    mana_colors_used = colors_used(card['cost'])

    if mana_colors_used == 'Colorless':
        if 'Artifact' in card['type']:
            return Image.open(os.path.join(subdir, 'pt_artifact.png'))
        elif 'Vehicle' in card['type']:
            return Image.open(os.path.join(subdir, 'pt_vehicle.png'))
        else:
            return Image.open(os.path.join(subdir, 'pt_colorless.png'))
    elif len(mana_colors_used) == 1:
        f_name = {'Black':'B', 'Green':'G', 'Red':'R', 'Blue':'U', 'White':'W'}[mana_colors_used.pop()]
        return Image.open(os.path.join(subdir, 'pt_' + f_name + '.png'))  # single colored mana
    else:
        return Image.open(os.path.join(subdir, 'pt_multicolored.png'))


def load_set_symbol(card):
    # returns image object for power / toughness overlay image
    # which image we load depends on card details

    subdir = '../image_templates/set_symbols'

    f_name = re.sub(' ', '_', card['rarity']).lower()
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
    #   inline symbols are sized and spaced appropriate to the font size
    #   honors whitespace most of the time
    #       honors newlines in the input text, forcing a newline at those locations, regardless of optimal spacing
    #       honors whitespace between words, except when a newline is inserted by this function (then it is dropped)
    #       honors leading whitespace only when it occurs either after a newline in the text, or at the beginning of the text
    #       drops all trailing whitespace
    # returns rendered image and boolean
    #   boolean indicates whether any words were broken up into multiple lines
    # long_token_mode changes the following behaviors, and should probably only be used for recursion
    #   text should be only one overly long word
    #   returns list of rendered lines (and no boolean), instead of one rendered image

    assert max_width > 0
    assert font_size > 0
    assert font_path

    if long_token_mode and len(text) == 1:
        raise FontTooLargeError(f'{text}, {max_width}, {font_path}, {font_size}, {long_token_mode}, {kwargs}')

    vertical_kerning, symbol_size, symbol_spacing = symbol_sizing(font_size)

    def token_encodes_symbols(token):
        # only allow properly encoded symbol groups without leading/trailing/middling nonsense
        #   which are guaranteed to be tokenized separately below
        return re.search(r'^(\{[^\}\{\s}]+\})+$', token) is not None

    # break text into symbols, newlines, words, and whitespace tokens in priority order
    #   which will be partitioned into rendered lines
    #   rendered lines will then be added together to form a rendered multiline text
    tokens = None
    text = text.strip()
    if not long_token_mode:
        # tokinize in two steps
        #   in the first step we extract just the encoded symbol groups, so that this syntax takes priority over word syntax
        #   and can extract properly encoded symbols from the middle of partial/malformated symbols
        #   eg '{{6}}' should be parsed as ['', '{', '', '{6}', '', '}', ''], and not as ['', '{{6}}', '']
        #   a single re.split with a '|' concatenated regex pattern would not be able to make that priority distinction due to greedyness
        tokens_one_deep = re.split(r'((?:\{[^\}\{\s}]+\})+)', text)
        tokens_two_deep = []
        for x in tokens_one_deep:
            if not token_encodes_symbols(x):  # finally, breakup the non-symbols into newlines, words, and whitespace
                 tokens_two_deep.extend(re.split(r'(\n|[^\s]+)', x))
            else:
                tokens_two_deep.append(x)

        # now since we did nested re.split calls, we'll have consecutive whitespace (or empty strings)
        # consolidate these, except newlines
        tokens = []
        for x in tokens_two_deep:
            whitespace_not_newlines = r'^[^\S\n]+$'
            if tokens and re.search(whitespace_not_newlines, tokens[-1]) and re.search(whitespace_not_newlines, x):
                tokens[-1] += x
            else:
                tokens.append(x)

    else:
        # either its fully symbols, or its not symbols at all, guaranteed from above
        if token_encodes_symbols(text):
            tokens = re.split(r'(\{[^\}]+\})', text)  # individual symbols
        else:
            tokens = re.split(r'(.)', text)  # individual characters

        # prevent infinite recursion. We should never fail this unless something is malformatted
        # 3 includes the beginning and end empty-string artifacts, so we're really looking for more than one proper-token
        assert len(tokens) > 3

    # beginning/ending empty strings are artifacts of the re.split
    #   clear the last, but keep the first, to get an even number of tokens
    #   tokens will be iterated over in pairs (whitespace, proper-token)
    # finally, make sure we get what we expect: a list where every odd-indexed token is whitespace (or empty string)
    assert tokens[0] == ''
    assert tokens[-1] == ''
    del tokens[-1]
    assert len(tokens) % 2 == 0, tokens
    for i, x in enumerate(tokens):
        if not i%2: assert re.search(r'^\s*$', x) is not None

    # construct test image for rendering size tests, but not for final text rendering
    im_test = Image.new(mode='RGBA', size=(1, 1))  # size is irrelevant
    d_test = ImageDraw.Draw(im_test)
    font = ImageFont.truetype(font_path, size=font_size)

    # Handle comma's rendered by themselves
    # most text renders along the same baseline by default
    #   however commas need a little special attention when rendered by themselves
    #   in order to render along the same baseline
    (left, top, right, bottom) = d_test.textbbox((0,0), ',1', font=font, anchor='lt')
    comma_height_override = bottom - top

    def render_text(t):
        # check size, and then render on a minimally sized image
        (left, top, right, bottom) = d_test.textbbox((0,0), t, font=font, anchor='lt')
        rendered_width = right - left
        rendered_height = bottom - top
        if re.search(r'^\s*(,\s*)+$', t):  # Handle comma's rendered by themselves
            rendered_height = comma_height_override
        im = Image.new(mode='RGBA', size=(rendered_width, rendered_height))
        d = ImageDraw.Draw(im)
        # its important here that we use the bottom anchor so that the comma ends up in the correct location with the comma_height_override
        d.text((0,rendered_height), text=t, font=font, anchor='lb', **kwargs)
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
    honor_leading_whitespace = True  # honor whitespace at beginning of text (if any)
    broken_token = False
    # render line of text, adding one word at a time, until max_width constraint violation
    while tokens:
        whitespace = tokens[0]
        token = tokens[1]
        token_adds = None
        cached_mana_render = None

        # try adding one token to the line, then check constraints
        if token == '\n':
            render_all_pending(render_None=True)

            # nothing further to compute for newlines
            # drop the trailing whitespace (if any)
            tokens.pop(0)  # pop twice
            tokens.pop(0)
            honor_leading_whitespace = True  # honor
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
            if consolidated_words or honor_leading_whitespace:
                token_text = consolidated_words + whitespace + token
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
                tokens.pop(0)  # pop twice
                tokens.pop(0)
                honor_leading_whitespace = False

        else:  # token fits on line
            if token_encodes_symbols(token):
                line_images.append(cached_mana_render)
            else:
                if consolidated_words or honor_leading_whitespace:
                    consolidated_words += whitespace
                consolidated_words += token
            tokens.pop(0)  # pop twice
            tokens.pop(0)
            honor_leading_whitespace = False

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
    sep_bar = sep_bar.resize((math.ceil(width * 0.95), 3))

    # prefer smaller fonts to broken tokens, unless font needs to be lowered below criterion
    largest_rendered_with_broken_token = None
    max_font_point_loss_to_unbreak_token = 10

    # parse main text for loyalty modifier symbols
    # partition main text if these are found
    # if these are not found, partitioned_main_text will be a list with only one element
    if card['main_text'] is not None:
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

        # render main text
        if card['main_text'] is not None:
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


def render_card(card, outdir, no_art, verbosity, trash_art_cache=False, art_dir=None):
    # image sizes and positions are all hard coded magic numbers
    # trash_art_cache causes the renderer to ignore and overwrite any cached art files, making fresh calls to txt2img
    # art_dir may be specified if the renderer is to use a non-default location for the art cache
    #   this is useful during render_yaml, when the source directory may already have an art cache we don't want to copy
    #   and when the destination directory is different from the source directory (ie preserve source renders, and create new ones to compare)

    # determine side ID for cards with multiple sides
    if ('a_side' in card or
        'b_side' in card or
        'c_side' in card or
        'd_side' in card or
        'e_side' in card):
        side_id = f'-{card["side"].upper()}'
    else:
        # single sided cards omit this field
        side_id = ''

    # determine card_file_name
    # the space in card_file_name is important for parsability
    #   because the name is guaranteed to not start with a space
    #   while it could (legally) start with "-A"
    card_file_name = f"{card['card_number']:05}{side_id} {card['name']}.png"

    # create a base image onto which everything else is composited
    # art is the lowest layer of the card, but we need a full size image to paste it into, since the art is not quite full sized
    im_card = Image.new(mode='RGBA', size=(1500, 2100), color=(0,0,0,0))

    # either load a cached art image, or create one
    if not no_art:
        art_dir = art_dir or os.path.join(outdir, 'art_cache')
        os.makedirs(art_dir, exist_ok=True)
        cache_path = os.path.join(art_dir, card_file_name)

        if not trash_art_cache and os.path.exists(cache_path):
            if verbosity > 2:
                print(f'using cached image')

            art = Image.open(cache_path)
            png_info = art.info['parameters']

        else:
            if verbosity > 2:
                print(f'sampling txt2img')

            art, png_info = sample_txt2img(card, cache_path, card['seed'] + card['seed_diff'], verbosity)

        # resize and crop the art to fit in the frame
        art = art.resize((1937, 1937))  # make sure we resize X and Y by the same ratio, and fit the frame in the Y dimension
        art = art.crop((218, 0, 1937-219, 1937))  # but then crop the left and right equally to fit the frame
        im_card.paste(art, box=(0, 0))

    # add the frame over the art
    frame = load_frame(card)
    im_card.alpha_composite(frame, dest=(0, 0))

    # TODO add legendary frame overlay

    # main mana cost
    if card['cost'] is not None:
        max_width = (RIGHT_TITLE_BOX_MANA - LEFT_TITLE_BOX) // 2
        im_mana = render_text_largest_fit(card['cost'], max_width, TITLE_MAX_HEIGHT, FONT_TITLE, 120)
        left_main_cost = RIGHT_TITLE_BOX_MANA - im_mana.width
        top_main_cost = HEIGHT_MID_TITLE - im_mana.height // 2
        im_card.alpha_composite(im_mana, dest=(left_main_cost, top_main_cost))
    else:
        left_main_cost = RIGHT_TITLE_BOX_TEXT  # zero width, adjusted for text spacing constraints

    # name
    # specifically don't crop title boxes, so that the text baseline is always in the same location
    #   ie the text doesn't shift around depending on whether it contains tall characters dropping below the baseline
    #   which would cause it to appear off center
    max_width = left_main_cost - LEFT_TITLE_BOX - 5
    im_text = render_text_largest_fit(card['name'], max_width, TITLE_MAX_HEIGHT, FONT_TITLE, DEFAULT_FONT_SIZE, crop_final=False, fill=(255,255,255,255))
    top = HEIGHT_MID_TITLE_TEXT - im_text.height // 2
    im_card.alpha_composite(im_text, dest=(LEFT_TITLE_BOX, top))

    # set symbol
    im_set = load_set_symbol(card)
    im_set = im_set.resize((97, 97))
    pos = (RIGHT_TITLE_BOX_MANA - im_set.width,
           HEIGHT_MID_TYPE - im_set.height // 2)
    im_card.alpha_composite(im_set, dest=pos)
    left_set = pos[0]

    # type - width constraints are almost the same as card title
    max_width = left_set - LEFT_TITLE_BOX - 5  # 5 is arbitrary spacing
    im_text = render_text_largest_fit(card['type'], max_width, TITLE_MAX_HEIGHT, FONT_TITLE, DEFAULT_FONT_SIZE, crop_final=False, fill=(255,255,255,255))
    top = HEIGHT_MID_TYPE_TEXT - im_text.height // 2
    im_card.alpha_composite(im_text, dest=(LEFT_TITLE_BOX, top))

    # power toughness
    #   first render the infobox overlay
    #   then render text on top of that
    if card['power_toughness'] is not None:
        im_pt = load_power_toughness_overlay(card)
        im_card.alpha_composite(im_pt, dest=(1137, 1858))  # magic numbers, image has assymetric partial alpha around the edges

        im_text = render_text_largest_fit(card['power_toughness'], 194, 82, FONT_MODULAR, DEFAULT_FONT_SIZE, fill=(0,0,0,255))
        top = 1928 - im_text.height // 2
        left = 1292 - im_text.width // 2
        im_card.alpha_composite(im_text, dest=(left, top))

    # loyalty
    if card['loyalty'] is not None:
        im_loyalty = Image.open('../image_templates/modular_elements/loyalty.png')
        im_card.alpha_composite(im_loyalty, dest=(1200, 1847))

        im_text = render_text_largest_fit(str(card['loyalty']), 154, 60, FONT_MODULAR, DEFAULT_FONT_SIZE, fill=(255,255,255,255))
        top = 1915 - im_text.height // 2
        left = 1314 - im_text.width // 2
        im_card.alpha_composite(im_text, dest=(left, top))

    # main text box
    im_main_text_box = render_main_text_box(card)
    im_card.alpha_composite(im_main_text_box, dest=(LEFT_MAIN_TEXT_BOX, TOP_MAIN_TEXT_BOX))

    # info text
    d = ImageDraw.Draw(im_card)
    font = ImageFont.truetype(FONT_TITLE, size=35)
    card_id = f'ID: {card["set_number"]:05}_{card["seed"]}+{card["seed_diff"]}_{card["card_number"]:05}{side_id}'
    d.text((100, 1971), text=card_id, font=font, anchor='lt', fill=(255,255,255,255))

    right = 1399
    if card['power_toughness'] is not None:
        right = 1166
    elif card['loyalty'] is not None:
        right = 1219
    d.text((right, 1971), text=card['timestamp'], font=font, anchor='rt', fill=(255,255,255,255))

    im_nn_names = render_text_largest_fit(', '.join(card['nns_names']), 1299, 35, FONT_TITLE, 35, fill=(255,255,255,255))
    im_card.alpha_composite(im_nn_names, dest=(100, 2022 - im_nn_names.height // 2))

    im_brush = Image.open('../image_templates/modular_elements/artistbrush.png')
    im_brush = im_brush.resize((40, 25))
    im_card.alpha_composite(im_brush, dest=(100, 2043 + 2))
    im_author = render_text_largest_fit(card['author'], 433, 35, FONT_TITLE, 35, fill=(255,255,255,255))
    right_author = 145 + im_author.width
    im_card.alpha_composite(im_author, dest=(145, 2059 - im_author.height // 2))

    repo_hash = base58.b58encode_int(int(card['repo_hash'], 16))
    repo_hash = repo_hash[:8]
    repo_hash = repo_hash.decode('utf-8')
    repo_info = f"{card['repo_link']} @{repo_hash}"
    width = 1399 - right_author - 35  # 35 is arbitrary spacing
    im_repo_info = render_text_largest_fit(repo_info, width, 35, FONT_TITLE, 35, fill=(255,255,255,255))
    im_card.alpha_composite(im_repo_info, dest=(1399 - im_repo_info.width, 2059 - im_repo_info.height // 2))

    # save image
    out_path = os.path.join(outdir, card_file_name)
    if not no_art:
        encoded_info = PngImagePlugin.PngInfo()
        encoded_info.add_text("parameters", png_info)
        im_card.save(out_path, pnginfo=encoded_info)
    else:
        im_card.save(out_path)

    # recurse on sides b-e
    if 'b_side' in card: render_card(card['b_side'], outdir, no_art, verbosity, trash_art_cache, art_dir)
    if 'c_side' in card: render_card(card['c_side'], outdir, no_art, verbosity, trash_art_cache, art_dir)
    if 'd_side' in card: render_card(card['d_side'], outdir, no_art, verbosity, trash_art_cache, art_dir)
    if 'e_side' in card: render_card(card['e_side'], outdir, no_art, verbosity, trash_art_cache, art_dir)


def render_yaml(yaml_path, outdir, no_art, verbosity, trash_art_cache, force_render_all):
    # renders cards stored in yaml file

    # default outdir to yaml location (ie overwrite existing renders)
    if outdir is None:
        outdir = os.path.dirname(yaml_path)

    # tell the renderer to use the art cache at the source if the destination doesn't have one
    dest_art_dir = os.path.join(outdir, 'art_cache')
    source_art_dir = os.path.join(os.path.dirname(yaml_path), 'art_cache')
    if os.path.exists(source_art_dir) and not os.path.exists(dest_art_dir):
        art_dir = source_art_dir
    else:
        art_dir = None

    # acquire cards from yaml
    f = open(yaml_path)
    cards = yaml.load(f.read())
    f.close()

    for card in cards:
        # replace 'a_side' backlinks, which are omitted from save file
        if 'b_side' in card: card['b_side']['a_side'] = card
        if 'c_side' in card: card['c_side']['a_side'] = card
        if 'd_side' in card: card['d_side']['a_side'] = card
        if 'e_side' in card: card['e_side']['a_side'] = card

        # decide whether this card will be rendered
        # this may be overriden below
        render = force_render_all

        # Handle manual override fields
        for field in cards:
            s = re.search(r'(.*)_override', field)
            if s is not None:
                card[s.group(1)] = card[field]
                render = True

        if render:
            render_card(card, outdir, no_art, verbosity, trash_art_cache, art_dir)


if __name__ =='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml_path", default=None, type=str, help="path to input yaml file, the same file output by generate_cards.py."
                                                                    " Resolves '*_override' keys in cards as overrides for default fields."
                                                                    " These are probably written by hand, if they exist,"
                                                                    " allowing you to retain both the original text and the hand-modified versions side-by-side.")
    parser.add_argument("--outdir", default=None, type=str, help="path to outdir. Files are saved directly in this folder. Defaults to same directory as yaml_path.")
    parser.add_argument("--no_art", action='store_true', help="disable txt2img render, which occupies most of the render time. Useful for debugging/testing.")
    parser.add_argument("--trash_art_cache", action='store_true', help="forces renderer to ignore and overwrite any cached art files, making fresh calls to txt2img."
                                                                       " Normally, the renderer will try to use cached art files, if they exist, to save tremendous amounts of time.")
    parser.add_argument("--force_render_all", action='store_true', help="Renders all cards in the input file. Default state is to only render cards which have '*_override' keys, likely saving tremendous amounts of time.")
    parser.add_argument("--verbosity", type=int, default=1)
    args = parser.parse_args()

    try:
        render_yaml(args.yaml_path, args.outdir, args.no_art, args.verbosity, args.trash_art_cache, args.force_render_all)
        terminate_A1SD_server(args.verbosity)
    except:
        terminate_A1SD_server(args.verbosity)
        raise

