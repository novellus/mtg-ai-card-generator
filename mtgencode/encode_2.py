import json
import pprint
import random
import re


def encode_names(j, args):
    # collect data from input
    names = []
    for s_key in list(j['data'].keys()):
        for card in j['data'][s_key]['cards']:
            names.append(card['name'])

    # randomize data order
    if not args.stable:
        random.shuffle(names)

    # write out data
    file_text = '\n'.join(names)

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
    parser.add_argument('--outfile_flavor',  default=None,                     help='postpend for flavor text file, for other external sources of data')
    parser.add_argument('-s', '--stable',    action='store_true',              help="don't randomize the order of the elements")
    parser.add_argument('-v', '--verbose',   action='store_true',              help='verbose output')
    
    args = parser.parse_args()
    main(args)
