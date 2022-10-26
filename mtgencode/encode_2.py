import json
import os
import pprint
import random
import re
import sys

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)
import cardlib


def encode_names(j, args):
    # collect data from input
    names = set()  # set for deduplication
    for s_key in list(j['data'].keys()):
        for card in j['data'][s_key]['cards']:
            _, processed_name = cardlib.process_name_field(card['name'])
            names.add(processed_name)

    names = sorted(list(names))

    # randomize data order
    # This should give a random but consistent ordering, to make comparing changes
    # between the output of different versions easier.
    if not args.stable:
        random.seed(1371367)
        random.shuffle(names)

    # write out data
    file_text = '\n'.join(names) + '\n'

    f = open(args.outfile_names, 'w')
    f.write(file_text)
    f.close()


def main(args):
    f = open(args.infile, encoding='UTF-8')
    j = json.loads(f.read())
    f.close()

    encode_names(j, args)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('infile',            default='data/AllPrintings.json', help='encoded card file or json corpus to encode')
    parser.add_argument('--outfile_names',                                     help='output file for encoded names')
    parser.add_argument('--outfile_flavor',                                    help='output file for encoded flavor text')
    parser.add_argument('--outfile_artists', default=None,                     help='output file for artist stats, default None')
    parser.add_argument('--extra_names',     default=None,                     help='postpend for names file, for other external sources of data')
    parser.add_argument('--extra_flavor',    default=None,                     help='postpend for flavor text file, for other external sources of data')
    parser.add_argument('-s', '--stable',    action='store_true',              help="don't randomize the order of the elements")
    parser.add_argument('-v', '--verbose',   action='store_true',              help='verbose output')
    
    args = parser.parse_args()
    main(args)
