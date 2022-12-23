import json
import re
import tabulate

from collections import defaultdict


def process_artist_field(s):
    s = s.lower()
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)  # no extraneous white space
    s = utils.to_ascii(s)

    return s


def artist_stats(j, args):
    # collect data from input
    data = defaultdict(int)
    for s_key in list(j['data'].keys()):
        for card in j['data'][s_key]['cards']:
            if 'artist' in card and card['artist']:
                processed_artist = process_artist_field(card['artist'])
                data[processed_artist] += 1

    # order data
    stats = sorted(list(data.items()), key=lambda x: x[1], reverse=True)

    # write out data
    headers = ['artist', 'count']
    file_text = tabulate.tabulate(stats, headers=headers)

    # file_text = f'{headers[0]}|{headers[1]}\n'
    # for entry in stats:
    #     file_text += f'{entry[0]}|{entry[1]}\n'

    f = open(args.outfile, 'w')
    f.write(file_text)
    f.close()


def main(args):
    f = open(args.infile, encoding='UTF-8')
    j = json.loads(f.read())
    f.close()

    artist_stats(j, args)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('infile',            default='data/AllPrintings.json', help='encoded card file or json corpus to encode')
    parser.add_argument('--outfile',         default=None,                     help='output file for artist stats, default None')
    parser.add_argument('-v', '--verbose',   action='store_true',              help='verbose output')
    
    args = parser.parse_args()
    main(args)
