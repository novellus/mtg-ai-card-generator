import json
import os
import pprint
import random
import re
import sys

from collections import namedtuple

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)
import cardlib
import utils


def stabilize_shuffles():
    # This should give a random but consistent ordering, to make comparing changes
    # between the output of different versions easier.
    random.seed(1371367)


def encode_names(j, args):
    # collect data from input
    names = set()  # set for deduplication
    for s_key in list(j['data'].keys()):
        for card in j['data'][s_key]['cards']:
            _, processed_name = cardlib.process_name_field(card['name'])
            names.add(processed_name)

    # TODO extra

    names = sorted(list(names))

    # randomize data order
    if not args.stable:
        random.shuffle(names)

    # write out data
    file_text = '\n'.join(names) + '\n'

    f = open(args.outfile_names, 'w')
    f.write(file_text)
    f.close()


def process_flavor_field(s):
    s = s.lower()
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)  # no extraneous white space
    s = utils.to_ascii(s)

    return s


def encode_flavor(j, args):
    # data type
    Card = namedtuple('Entry', ['name', 'flavor'])

    # collect data from input
    data = set()  # set for deduplication
    for s_key in list(j['data'].keys()):
        for card in j['data'][s_key]['cards']:
            if 'flavorText' in card and card['flavorText']:
                _, processed_name = cardlib.process_name_field(card['name'])
                processed_flavor = process_flavor_field(card['flavorText'])

                data.add(Card(
                    name = processed_name,
                    flavor = processed_flavor,
                ))

    # TODO extra

    data = sorted(data, key = lambda x: x.name)

    # randomize data order
    if not args.stable:
        random.shuffle(data)

    # write out data
    file_text = ''
    for entry in data:
        file_text += f'{entry.name}|{entry.flavor}\n'

    f = open(args.outfile_flavor, 'w')
    f.write(file_text)
    f.close()


def main(args):
    f = open(args.infile, encoding='UTF-8')
    j = json.loads(f.read())
    f.close()

    stabilize_shuffles()

    encode_names(j, args)
    encode_flavor(j, args)
    # TODO artist stats


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
