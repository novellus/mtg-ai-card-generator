import argparse
import os
import pprint
import re
import yaml

import encode
import render
from generate_cards import FIELD_ORDER


def is_threat_removal(card):
    if 'main_text' not in card or card['main_text'] is None:
        return False
    else:
        return re.search('damage to target creature|destroy target creature|exile target creature', card['main_text']) is not None

def is_color_combination(card, color_combo):
    if 'cost' not in card or card['cost'] is None:
        return False
    else:
        colors_used = render.colors_used(card['cost'])
        uses_all_required_colors = all([c in colors_used for c in color_combo])
        uses_other_colors = any([c not in color_combo for c in colors_used])
        return uses_all_required_colors and not uses_other_colors


def main(args):
    if os.path.exists(args.out_path):
        print(f'Overwriting target path! {args.out_path}')

    args.yaml_paths = re.split(r'\s*,\s*', args.yaml_paths)

    print(f'Loading {len(args.yaml_paths)} yaml files')

    cards = []
    for yaml_path in args.yaml_paths:
        assert os.path.exists(yaml_path), yaml_path
        assert args.out_path != yaml_path

        f = open(yaml_path)
        cards.extend(yaml.load(f.read(), Loader=yaml.FullLoader))
        f.close()

    print(f'Searching {len(cards)} cards')

    extract = []
    for card in cards:
        if is_color_combination(card, ['White', 'Black', 'Green']):
            extract.append(card)

    print(f'Found {len(extract)} matching cards')

    yaml_data = [encode.order_dict_fields(card, FIELD_ORDER) for card in extract]
    f = open(args.out_path, 'w')
    f.write(yaml.dump(yaml_data, sort_keys=False))
    f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml_paths", type=str, help="path to card_data.yaml file, or comma separated list of paths to multiple yamls")
    parser.add_argument("--out_path", type=str, help="path to output file")
    args = parser.parse_args()

    main(args)
