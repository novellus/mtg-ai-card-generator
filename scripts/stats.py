import argparse
import os
import re
import yaml

from collections import defaultdict

# local imports
import render


def compute_stats(cards, outpath):
    # organize cards into bins, which will be used to compute stats
    # each card may be present in more than one bin

    costless = []  # this list is probably largely invalid cards...
    colorless = []
    colorless_artifacts = []
    mono_colored = defaultdict(list)  # {color: []}
    multicolored = defaultdict(list)  # {'colorA, colorB': []}, including 'three_or_more' as a key
    multisided = defaultdict(list)  # {num_sides: []}
    mana_value = defaultdict(list)  # {value: []}  # AKA converted mana cost
    authors = defaultdict(list)  # {value: []}
    num_cards = len(cards)
    num_sides = 0

    # main types only, including an 'Other' key for cards not in any included category
    mono_main_types = {'Land':[], 'Creature':[], 'Artifact':[], 'Enchantment':[], 'Planeswalker':[], 'Instant':[], 'Sorcery':[], 'Scheme':[], 'Contraption':[], 'Siege':[], 'Other':[]}
    multi_main_types = defaultdict(list)

    for card in cards:
        # aggregate sides for iteration
        sides = [card]
        if 'b_side' in card: sides.append(card['b_side'])
        if 'c_side' in card: sides.append(card['c_side'])
        if 'd_side' in card: sides.append(card['d_side'])
        if 'e_side' in card: sides.append(card['e_side'])
        num_sides += len(sides)

        # determine colors used in card, including each side
        colors = set()
        found_colorless = False
        for side in sides:
            side_colors = render.colors_used(side['cost'])
            if side_colors is None:
                continue
            elif side_colors == 'Colorless':
                found_colorless = True
            else:
                colors.update(side_colors)

        colors = colors or None
        if found_colorless:
            colors = colors or 'Colorless'

        # simplify colors sytax for human readability
        #   set of one str -> str
        #   set of 2 str -> 'str1, str2', since a list isn't hashable, and a tuple makes the yaml parser put extra ugly junk in the output file
        #   set of 3 or more -> 'three_or_more' to consolidate rare combinations into one key
        if type(colors) == set:
            if len(colors) == 1:
                colors = colors.pop()
            elif len(colors) == 2:
                colors = ', '.join(sorted(colors))
            else:
                colors = 'three_or_more'

        # finally, catagorize card by color
        if colors is None:
            costless.append(card)
        elif colors == 'Colorless':
            colorless.append(card)
        elif ',' not in colors and colors != 'three_or_more':
            mono_colored[colors].append(card)
        else:
            multicolored[colors].append(card)

        # catagorize by mana value
        # only the front face of the card is considered, per https://mtg.fandom.com/wiki/Mana_value
        #   unless its a split card, which we're just gonna ignore here
        value = 0
        if card['cost'] is not None:
            for sym in render.parse_mana_symbols(card['cost']):
                s = re.search(r'^\d+$', sym)
                if s is not None:
                    value += int(sym)
                else:
                    value += 1
        if value > 0 or 'Land' not in card['type']:  # Don't count Lands as 0 CMC
            mana_value[value].append(card)

        # catagorize by main type
        # determine types used in card, including each side
        # this only considers the type field of the card, while the other card attributes may not be consistent with this
        #   eg a card may have a 'Planeswalker' type listed, but not actually have a loyalty counter
        # this also only parses for exact matches, misspellings will catagorize as "Other"
        types = set()
        found_colorless = False
        for side in sides:
            side_types = [type_string for type_string in mono_main_types if type_string != 'Other' and type_string in side['type']]
            if not side_types:
                side_types = ['Other']
            types.update(side_types)

        assert len(types) > 0, f'got a typesless card, which should be impossible, since it could catagorize as "Other": {str(card)}'
        if len(types) == 1:
            mono_main_types[types.pop()].append(card)
        else:
            multi_main_types[', '.join(sorted(list(types)))].append(card)

        # catagorize colorless artifacts
        if colors == 'Colorless' and 'Artifact' in card['type']:
            colorless_artifacts.append(card)

        # catagorize multisided cards
        if len(sides) > 1:
            multisided[len(sides)].append(card)

        # tabulate authors
        for side in sides:
            authors[side['author']].append(card)

    avg_sides = num_sides / num_cards

    # ID function, which is enough info to efficiently lookup the rendered file by hand, or lookup the card in the yaml
    card_id = lambda card: f"{card['card_number']:05}, {card['name']}"

    stats = {
        '_avg_sides_per_card'      : avg_sides,
        '_num_cards'               : num_cards,
        '_num_colorless'           : len(colorless),
        '_num_colorless_artifacts' : len(colorless_artifacts),
        '_num_costless'            : len(costless),
        '_num_mono_main_types'     : {k:len(v) for k,v in mono_main_types.items()},
        '_num_multi_main_types'    : {k:len(v) for k,v in multi_main_types.items()},
        '_num_mana_value'          : {k:len(v) for k,v in mana_value.items()},
        '_num_mono_colored'        : {k:len(v) for k,v in mono_colored.items()},
        '_num_multicolored'        : {k:len(v) for k,v in multicolored.items()},
        '_num_multisided'          : {k:len(v) for k,v in multisided.items()},
        '_num_authors'             : {k:len(v) for k,v in authors.items()},
        'colorless'                : sorted([card_id(card) for card in colorless]),
        'colorless_artifacts'      : sorted([card_id(card) for card in colorless_artifacts]),
        'costless'                 : sorted([card_id(card) for card in costless]),
        'mono_main_types'          : {k: [card_id(card) for card in v] for k,v in mono_main_types.items()},
        'multi_main_types'         : {k: [card_id(card) for card in v] for k,v in multi_main_types.items()},
        'mana_value'               : {k: [card_id(card) for card in v] for k,v in mana_value.items()},
        'mono_colored'             : {k: [card_id(card) for card in v] for k,v in mono_colored.items()},
        'multicolored'             : {k: [card_id(card) for card in v] for k,v in multicolored.items()},
        'multisided'               : {k: [card_id(card) for card in v] for k,v in multisided.items()},
        'authors'                  : {k: [card_id(card) for card in v] for k,v in authors.items()},
    }

    f = open(outpath, 'w')
    f.write(yaml.dump(stats))
    f.close()


def stats_from_yaml(yaml_path, outpath):
    # reads in yaml file, parses it into cards, and executes main stats function on those cards

    assert not os.path.exists(args.outpath), "Target outpath already exists"

    # acquire cards from yaml
    f = open(yaml_path)
    cards = yaml.load(f.read(), Loader=yaml.FullLoader)
    f.close()

    # replace 'a_side' backlinks, which are omitted from save file
    for card in cards:
        if 'b_side' in card: card['b_side']['a_side'] = card
        if 'c_side' in card: card['c_side']['a_side'] = card
        if 'd_side' in card: card['d_side']['a_side'] = card
        if 'e_side' in card: card['e_side']['a_side'] = card

    compute_stats(cards, outpath)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml_path", type=str, help="path to input yaml file, the same file (or file format) output by generate_cards.py.")
    parser.add_argument("--outpath", type=str, help="path to output file.")
    args = parser.parse_args()

    stats_from_yaml(args.yaml_path, args.outpath)
