import argparse
import os
import pprint
import re
import yaml

import encode
from generate_cards import FIELD_ORDER


def is_threat_removal(card):
    if 'main_text' not in card or card['main_text'] is None:
        return False
    else:
        return re.search('damage to target creature|destroy target creature|exile target creature', card['main_text']) is not None


def main(args):
    assert os.path.exists(args.yaml_path)
    assert args.out_path != args.yaml_path
    if os.path.exists(args.out_path):
        print(f'Overwriting target path! {args.out_path}')

    f = open(args.yaml_path)
    cards = yaml.load(f.read(), Loader=yaml.FullLoader)
    f.close()

    extract = []
    for card in cards:
        if is_threat_removal(card):
            extract.append(card)

    print(f'Found {len(extract)} matching cards')

    yaml_data = [encode.order_dict_fields(card, FIELD_ORDER) for card in extract]
    f = open(args.out_path, 'w')
    f.write(yaml.dump(yaml_data, sort_keys=False))
    f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml_path", type=str, help="path to card_data.yaml file")
    parser.add_argument("--out_path", type=str, help="path to output file")
    args = parser.parse_args()

    main(args)
