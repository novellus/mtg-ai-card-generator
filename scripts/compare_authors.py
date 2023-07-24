# Compare author fields between an original yaml generation and a hand-composited list with hand-edited modifications to some of the entries. 
# Used to list cards whose author field has not been changed, and which thus need correction.

import argparse
import os
import pprint
import re
import yaml

from collections import defaultdict

import encode
import render
from generate_cards import FIELD_ORDER


def main(args):
    assert os.path.isdir(args.outdir)

    args.orig_yaml_paths = re.split(r'\s*,\s*', args.orig_yaml_paths)
    print(f'Loading {len(args.orig_yaml_paths)} yaml files')
    cards_orig = []
    for yaml_path in args.orig_yaml_paths:
        assert os.path.exists(yaml_path), yaml_path
        assert args.outdir != yaml_path

        f = open(yaml_path)
        cards_orig.extend(yaml.load(f.read(), Loader=yaml.FullLoader))
        f.close()

    args.final_composite = re.split(r'\s*,\s*', args.final_composite)
    print(f'Loading {len(args.final_composite)} yaml files')
    cards_changed = []
    for yaml_path in args.final_composite:
        assert os.path.exists(yaml_path), yaml_path
        assert args.outdir != yaml_path

        f = open(yaml_path)
        cards_changed.extend(yaml.load(f.read(), Loader=yaml.FullLoader))
        f.close()

    print(f'Organizing {len(cards_orig)} original cards')
    lookup_orig = defaultdict(dict)  # {set: {card_num: card}}
    for card in cards_orig:
        lookup_orig[card['set_number']][card['card_number']] = card

    limited_orig = []
    unable_to_lookup = []
    for card in cards_changed:
        try:
            limited_orig.append(lookup_orig[card['set_number']][card['card_number']])
        except:
            limited_orig.append({})
            unable_to_lookup.append(card)
            # print(f'Unable to find lookup card')
            # pprint.pprint(card)
            # raise  # TODO fix top unique seed diff in case of copied cards

    # generate list of incorrect authors
    orig_unchanged_authors = []
    new_unchanged_authors = []
    for i_card, card_orig in enumerate(limited_orig):
        card_changed = cards_changed[i_card]

        card_orig = encode.limit_fields(card_orig, blacklist=['nns_names'])
        card_changed = encode.limit_fields(card_changed, blacklist=['nns_names'])

        if card_orig != {}:
            if card_changed != card_orig:
                if card_changed['author'] == card_orig['author']:
                    orig_unchanged_authors.append(card_orig)
                    new_unchanged_authors.append(card_changed)



    print(f'Found {len(limited_orig)} limited_orig cards')
    print(f'Found {len(unable_to_lookup)} unable_to_lookup cards')
    print(f'Found {len(new_unchanged_authors)} unchanged_authors cards')


    yaml_data = [encode.limit_fields(card, blacklist=['nns_names']) for card in limited_orig]
    yaml_data = [encode.order_dict_fields(card, FIELD_ORDER) for card in yaml_data]
    f = open(os.path.join(args.outdir, 'compare_orig.yaml'), 'w')
    f.write(yaml.dump(yaml_data, sort_keys=False))
    f.close()

    yaml_data = [encode.limit_fields(card, blacklist=['nns_names']) for card in cards_changed]
    yaml_data = [encode.order_dict_fields(card, FIELD_ORDER) for card in yaml_data]
    f = open(os.path.join(args.outdir, 'compare_new.yaml'), 'w')
    f.write(yaml.dump(yaml_data, sort_keys=False))
    f.close()

    yaml_data = [encode.limit_fields(card, blacklist=['nns_names']) for card in unable_to_lookup]
    yaml_data = [encode.order_dict_fields(card, FIELD_ORDER) for card in yaml_data]
    f = open(os.path.join(args.outdir, 'compare_unable_to_lookup.yaml'), 'w')
    f.write(yaml.dump(yaml_data, sort_keys=False))
    f.close()

    yaml_data = [encode.limit_fields(card, blacklist=['nns_names']) for card in orig_unchanged_authors]
    yaml_data = [encode.order_dict_fields(card, FIELD_ORDER) for card in yaml_data]
    f = open(os.path.join(args.outdir, 'compare_orig_unchanged_authors.yaml'), 'w')
    f.write(yaml.dump(yaml_data, sort_keys=False))
    f.close()

    yaml_data = [encode.limit_fields(card, blacklist=['nns_names']) for card in new_unchanged_authors]
    yaml_data = [encode.order_dict_fields(card, FIELD_ORDER) for card in yaml_data]
    f = open(os.path.join(args.outdir, 'compare_new_unchanged_authors.yaml'), 'w')
    f.write(yaml.dump(yaml_data, sort_keys=False))
    f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--orig_yaml_paths", type=str, help="path to card_data.yaml file, or comma separated list of paths to multiple yamls")
    parser.add_argument("--final_composite", type=str, help="path to card_data.yaml file, or comma separated list of paths to multiple yamls")
    parser.add_argument("--outdir", type=str, help="dir path for output files")
    args = parser.parse_args()

    main(args)
