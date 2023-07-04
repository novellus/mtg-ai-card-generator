import argparse
import os
import pprint
import re

from collections import defaultdict
from collections import namedtuple
from fpdf import FPDF
from PIL import Image


def main(folder, verbosity=0):
    if verbosity > 0:
        print(f'Assembling a printable pdf from front/back images at {folder}, (slow)')

    assert os.path.isdir(folder)

    # collect image files from dest folder
    images = defaultdict(dict)  # {base_num: {'front': image, 'back': image}}
    for f_name in next(os.walk(folder))[2]:
        s = re.search(r'^(\d+)-(front|back)\.png$', f_name)
        if s is not None:
            base_num, side = s.groups()
            path = os.path.join(folder, f_name)
            images[base_num][side] = path

    # composite images onto pdf pages
    # in 4x2 grids, rotated 90 degrees to landscape format
    #   we could fit 10 cards per page if we have zero margins to edge or twixt
    #   but that also makes our life hard when cutting them apart, so we'll use margin
    ppi = 72  # base library uses 72 points per inch by default, and apparently that can't be configured
    bg_dpi = 300
    pdf_width = 11 * ppi
    pdf_height = 8.5 * ppi
    pdf = FPDF(orientation='L', unit='pt', format=(pdf_height, pdf_width))
    pdf.set_margins(0, 0)  # disable library margins, I'll compute my own
    pdf.set_compression(False)

    num_cols = 4
    num_rows = 2
    page_every = num_cols * num_rows

    # 2.5 x 3.5 in = standard playing card size
    #   set total avg width to 1/32 less than 2.5, for margin to card sleeves
    #   set space between cards for only one cut, with no extra trimming steps
    im_width = (2.5 - 3/32) * ppi
    im_height = (3.5 - 3/32) * ppi
    twixt_margin = 1/16 * ppi  # space between cards
    trim_here_line_thickness = int((twixt_margin / 3) / ppi * bg_dpi)
    trim_here_len = int((im_width / 20) / ppi * bg_dpi)
    x_margin = (pdf_width  - (im_width  * num_cols) - (twixt_margin * (num_cols - 1))) / 2
    y_margin = (pdf_height - (im_height * num_rows) - (twixt_margin * (num_rows - 1))) / 2

    # verify math makes sense. Make sure page margins are greater than zero, and also at least twixt_margin
    assert x_margin > twixt_margin, x_margin
    assert y_margin > twixt_margin, y_margin
    assert trim_here_line_thickness > 0, trim_here_line_thickness
    assert trim_here_len > 0, trim_here_len

    # construct black background image to layer behind card images, with same surrounding margins as twixt_margin
    bg_size = (int((pdf_width  - x_margin*2 + twixt_margin*2) / ppi * bg_dpi),
               int((pdf_height - y_margin*2 + twixt_margin*2) / ppi * bg_dpi))
    im_background = Image.new(mode='RGBA', size=bg_size, color=(0, 0, 0, 255))

    # add small trim-here marks to background, at card corners
    cross = Image.new(mode='RGBA', size=(trim_here_len, trim_here_len), color=(0, 0, 0, 255))
    cross_vertical   = Image.new(mode='RGBA', size=(trim_here_line_thickness, trim_here_len),            color=(255, 255, 255, 255))
    cross_horizontal = Image.new(mode='RGBA', size=(trim_here_len,            trim_here_line_thickness), color=(255, 255, 255, 255))
    cross.alpha_composite(cross_vertical  , dest=(int(trim_here_len / 2 - trim_here_line_thickness / 2), 0))
    cross.alpha_composite(cross_horizontal, dest=(0, int(trim_here_len / 2 - trim_here_line_thickness / 2)))
    for col in range(0, num_cols + 1):
        for row in range(0, num_rows + 1):
            x = int(-(cross.width  / 2) + (((twixt_margin / 2) + col * (twixt_margin + im_width )) / ppi * bg_dpi))
            y = int(-(cross.height / 2) + (((twixt_margin / 2) + row * (twixt_margin + im_height)) / ppi * bg_dpi))
            im_background.alpha_composite(cross, dest=(x, y))
    path_background = os.path.join(folder, 'pdf_background.png')
    im_background.save(path_background)

    # finally, add the images to the pdf
    row = 0
    col = 0
    back_images = defaultdict(list)  # [row: [image, image, ...]]
    for i, (base_num, sides) in enumerate(sorted(images.items())):
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
                      w = im_background.width  / bg_dpi * ppi,
                      h = im_background.height / bg_dpi * ppi)

        if verbosity > 1:
            print(f'PDF - embedding image {i+1} / {len(images)}')

        # add card images
        x = x_margin + col * (twixt_margin + im_width)
        y = y_margin + row * (twixt_margin + im_height)
        pdf.image(sides['front'], x=x, y=y, w=im_width, h=im_height)

        # stash background images in-order for the next page
        back_images[row].append(sides['back'])

        # add collated background images after every page, or after the last image
        if (not ((i + 1) % page_every)) or (i == (len(images) - 1)):
            pdf.add_page()

            pdf.image(path_background, 
                      x = x_margin - twixt_margin,
                      y = y_margin - twixt_margin,
                      w = im_background.width  / bg_dpi * ppi,
                      h = im_background.height / bg_dpi * ppi)

            for back_row, backs in back_images.items():
                for back_col, back_path in enumerate(reversed(backs)):  # reverse order to flip along short-side of the paper
                    if verbosity > 1:
                        print(f'PDF - embedding back image {back_col + back_row * num_cols} / {sum([len(v) for k,v in back_images.items()])}')

                    x = x_margin + back_col * (twixt_margin + im_width)
                    y = y_margin + back_row * (twixt_margin + im_height)
                    pdf.image(back_path, x=x, y=y, w=im_width, h=im_height)

            back_images = defaultdict(list)

        # track col
        col += 1

    pdf.output(name = os.path.join(folder, 'printable_cards.pdf'))

    # cleanup temp files
    os.remove(path_background)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collects all rendered card image files from the specified folder,'
                                                 ' and creates a printable pdf of them.'
                                                 ' Card backs are included on collated pages for double sided printing: flip over short edge.')
    parser.add_argument("--folder", type=str, help="path to folder containing card images in png format. Output pdf is also written to this folder.")
    args = parser.parse_args()

    main(args.folder)
