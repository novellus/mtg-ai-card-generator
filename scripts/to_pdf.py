import argparse
import os
import pprint
import re

from collections import defaultdict
from collections import namedtuple
from fpdf import FPDF
from PIL import Image
from PIL import PngImagePlugin


placement = namedtuple('placement', ['rotate', 'resize', 'dest'])  # these functions are performed in this order
def render_multisided_card_face(sides, out_path):
    # combines specified side files into one image file

    sub_sizes = {'full'    : (1500, 2100),  # normal orientation
                 'half'    : (1470, 1050),  # for use under 90 degrees rotation, slightly low on x axis to keep scale
                 'quarter' : ( 750, 1050),  # for use in normal orientation
                 'eigth'   : ( 735,  525),  # for use under 90 degrees rotation, slightly low on x axis to keep scale
                }

    # spec layout based on number of sides
    if len(sides) == 2:
        # side by side, 90 degrees sideways
        layout = {'A': placement(rotate=-90, resize=sub_sizes['half'],    dest=(15,  0)),
                  'B': placement(rotate=-90, resize=sub_sizes['half'],    dest=(15,  1050)),
                 }

    elif len(sides) == 3:
        # same as above, except B+C share the above's B slot, and are oriented normally
        layout = {'A': placement(rotate=-90, resize=sub_sizes['half'],    dest=(15,  0)),
                  'B': placement(rotate=0,   resize=sub_sizes['quarter'], dest=(0,   1050)),
                  'C': placement(rotate=0,   resize=sub_sizes['quarter'], dest=(750, 1050)),
                 }

    elif len(sides) == 4:
        # all 4 sides use a simple quarter of the card face
        layout = {'A': placement(rotate=0,   resize=sub_sizes['quarter'], dest=(0,   0)),
                  'B': placement(rotate=0,   resize=sub_sizes['quarter'], dest=(750, 0)),
                  'C': placement(rotate=0,   resize=sub_sizes['quarter'], dest=(0,   1050)),
                  'D': placement(rotate=0,   resize=sub_sizes['quarter'], dest=(750, 1050)),
                 }

    elif len(sides) == 5:
        # 3 sides use a simple quarter of the card face, and the remaining two sides share the last quarter, rotated sideways
        layout = {'A': placement(rotate=0,   resize=sub_sizes['quarter'], dest=(0,   0)),
                  'B': placement(rotate=0,   resize=sub_sizes['quarter'], dest=(750, 0)),
                  'C': placement(rotate=0,   resize=sub_sizes['quarter'], dest=(0,   1050)),
                  'D': placement(rotate=-90, resize=sub_sizes['eigth'],   dest=(750, 1050)),
                  'E': placement(rotate=-90, resize=sub_sizes['eigth'],   dest=(750, 1575)),
                 }

    else:
        raise ValueError(f'Unexpected number of sides, expected 2-5, found {len(sides)}: {sides}')

    # composite images together, according to hte specified layout
    # include the png_info from the A side, since that contains nested info about the other sides
    im_composite = Image.new(mode='RGBA', size=(1500, 2100), color=(0,0,0,0))
    encoded_info = PngImagePlugin.PngInfo()
    for side, path in sides.items():
        p = layout[side]
        im = Image.open(path)

        if side == 'A':
            encoded_info.add_text("parameters", im.info['parameters'])
            encoded_info.add_text("card_text", im.info['card_text'])

        if p.rotate != 0:
            im = im.rotate(p.rotate, expand=True)
        im = im.resize(p.resize)
        im_composite.alpha_composite(im, dest=p.dest)

    im_composite.save(out_path, pnginfo=encoded_info)


def main(args):
    assert os.path.isdir(args.folder)

    # collect image files from dest folder
    images = []
    multisided_images = defaultdict(dict)  # {'00000': {'A': '00000-A Card Name.png'}}
    for f_name in next(os.walk(args.folder))[2]:
        if re.search(r'\.png$', f_name) and not re.search(r'^(\d+_composite|pdf_background)\.png$', f_name):
            side_path = os.path.join(args.folder, f_name)

            # collect multi-sided cards separately, to be rendered together later
            s = re.search(r'^(\d+)-([ABCDE]) ', f_name)
            if s is not None:
                base_num, side = s.groups()
                out_path = os.path.join(args.folder, f'{base_num}_composite.png')
                multisided_images[out_path][side] = side_path

            else:
                images.append(side_path)

    # render multi-sided cards into one face image
    garbage_collect = []  # delete these when finished
    for out_path, sides in multisided_images.items():
        render_multisided_card_face(sides, out_path)
        images.append(out_path)
        garbage_collect.append(out_path)

    # composite images onto pdf pages
    # in 4x2 grids, rotated 90 degrees to landscape format
    #   we could fit 10 cards per page if we have zero margins to edge or twixt
    #   but that also makes our life hard when cutting them apart, so we'll use margin
    ppi = 72  # base library uses 72 points per inch by default, and apparently that can't be configured
    pdf_width = 11 * ppi
    pdf_height = 8.5 * ppi
    pdf = FPDF(orientation='L', unit='pt', format=(pdf_height, pdf_width))
    pdf.set_margins(0, 0)  # disable library margins, I'll compute my own
    pdf.set_compression(False)

    num_cols = 4
    num_rows = 2
    page_every = num_cols * num_rows

    im_width = 2.5 * ppi  # standard playing card size
    im_height = 3.5 * ppi
    twixt_margin = 0.1 * ppi  # space between cards
    x_margin = (pdf_width - (im_width * num_cols) - (twixt_margin * (num_cols - 1))) / 2
    y_margin  = (pdf_height - (im_height * num_rows) - (twixt_margin * (num_rows - 1))) / 2

    # verify math makes sense. Make sure page margins are greater than zero, and also at least twixt_margin
    assert x_margin > twixt_margin, x_margin
    assert y_margin > twixt_margin, y_margin

    # construct black background image to layer behind card images, with same surrounding margins as twixt_margin
    bg_size = (int(pdf_width  - x_margin*2 + twixt_margin*2),
               int(pdf_height - y_margin*2 + twixt_margin*2))
    im_background = Image.new(mode='RGBA', size=bg_size, color=(0, 0, 0, 255))
    path_background = os.path.join(args.folder, 'pdf_background.png')
    im_background.save(path_background)
    garbage_collect.append(path_background)

    # finally, add the images to the pdf
    row = 0
    col = 0
    for i, path in enumerate(images):
        # track row
        if not (col % num_cols):
            row += 1
            col = 0

        # add pages
        if not (i % page_every):
            pdf.add_page()
            row = 0
            col = 0

            # add background
            pdf.image(path_background, 
                      x = x_margin - twixt_margin,
                      y = y_margin - twixt_margin,
                      w = im_background.width,
                      h = im_background.height)

        # add card images
        x = x_margin + col * (twixt_margin + im_width)
        y = y_margin + row * (twixt_margin + im_height)
        pdf.image(path, x=x, y=y, w=im_width, h=im_height)
        col += 1

    pdf.output(name = os.path.join(args.folder, 'printable_cards.pdf'))

    # cleanup temp files
    for path in garbage_collect:
        os.remove(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collects all rendered card image files from the specified folder,'
                                                 ' and creates a printable pdf of them.'
                                                 ' Card backs are included on collated pages for double sided printing.'
                                                 ' Multi-sided cards are rendered into a single card face,'
                                                 ' either side-by-side or arrayed as appropriate')
    parser.add_argument("--folder", type=str, help="path to folder containing card images in png format. Output pdf is also written to this folder.")
    args = parser.parse_args()

    main(args)
