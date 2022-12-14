import argparse
import copy
import json
import pprint
import re
import titlecase

from collections import defaultdict


# internally formatted cards have the following fields. Fields are always present except those indicated as optional
# {
#     'a_side'          : internal format, optional, links to parent, present only on b-, c-, d-, and e- side cards
#     'b_side'          : internal format, optional, present only on a-side (top-level) cards
#     'c_side'          : internal format, optional, present only on a-side (top-level) cards
#     'cost'            : str or None
#     'd_side'          : internal format, optional, present only on a-side (top-level) cards
#     'e_side'          : internal format, optional, present only on a-side (top-level) cards
#     'flavor'          : str or None
#     'loyalty'         : str or None
#     'main_text'       : str
#     'maintypes'       : list of str (possibly empty)
#     'name'            : str
#     'num_sides'       : int (1-5), optional, present only on a-side (top-level) cards
#     'power_toughness' : 2-list of str or None
#     'rarity'          : str
#     'subtypes'        : list of str (possibly empty)
#     'supertypes'      : list of str (possibly empty)
# }


def extend_all_cases(l):
    # extends a list l with all reasonable cases for its original contents
    new = []
    new.extend([titlecase.titlecase(x) for x in l])
    new.extend([x.capitalize() for x in l])
    new.extend([x.upper() for x in l])
    new.extend([x.lower() for x in l])
    return list(set(new + l))


# constants describing mtg card attributes. These may need to be updated whenever new mechanics are released.

MTG_COUNTERS = ['Acorn', 'Aegis', 'Age', 'Aim', 'Arrow', 'Arrowhead', 'Awakening', 'Blaze', 'Blood', 'Bloodline', 'Book', 'Bounty', 'Bribery', 'Brick', 'Cage',
                'Carrion', 'Charge', 'Coin', 'Collection', 'Component', 'Contested', 'Corpse', 'Corruption', 'CRANK!', 'Credit', 'Croak', 'Crystal', 'Cube',
                'Currency', 'Death', 'Deathtouch ', 'Delay', 'Depletion', 'Descent', 'Despair', 'Devotion', 'Divinity', 'Doom', 'Double strike ', 'Dream', 'Echo',
                'Egg', 'Elixir', 'Ember', 'Energy', 'Enlightened', 'Eon', 'Experience', 'Eyeball', 'Eyestalk', 'Fade', 'Fate', 'Feather', 'Fetch', 'Filibuster',
                'First strike ', 'Flame', 'Flood', 'Flying', 'Foreshadow', 'Fungus', 'Fury', 'Fuse', 'Gem', 'Ghostform', 'Glyph', 'Gold', 'Growth', 'Hack',
                'Harmony', 'Hatching', 'Hatchling', 'Healing', 'Hexproof', 'Hit', 'Hone', 'Hoofprint', 'Hour', 'Hourglass', 'Hunger', 'Ice', 'Incarnation',
                'Indestructible', 'Infection', 'Ingenuity', 'Intel', 'Intervention', 'Invitation', 'Isolation', 'Javelin', 'Judgment', 'Keyword', 'Ki', 'Kick',
                'Knickknack', 'Knowledge', 'Landmark', 'Level', 'Lifelink', 'Lore', 'Loyalty', 'Luck', 'Magnet', 'Manabond', 'Manifestation', 'Mannequin',
                'Matrix', 'Menace', 'Midway', 'Mine', 'Mining', 'Mire', 'Music', 'Muster', 'Necrodermis', 'Net', 'Night', 'Omen', 'Ore', 'Page', 'Pain',
                'Palliation', 'Paralyzation', 'Pause', 'Petal', 'Petrification', 'Phylactery', 'Phyresis', 'Pin', 'Plague', 'Plot', 'Point', 'Poison', 'Polyp',
                'Pressure', 'Prey', 'Pupa', 'Quest', 'Reach', 'Ritual', 'Rope', 'Rust', 'Scream', 'Scroll', 'Shell', 'Shield', 'Shred', 'Silver', 'Sleep',
                'Sleight', 'Slime', 'Slumber', 'Soot', 'Soul', 'Spark', 'Spite',  'Spore', 'Stash', 'Storage', 'Strife', 'Study', 'Stun', 'Suspect', 'Task',
                'Theft', 'Ticket', 'Tide', 'Time', 'Tower', 'Training', 'Trample', 'Trap', 'Treasure', 'Unity', 'Valor', 'Velocity', 'Verse', 'Vigilance',
                'Vitality', 'Void', 'Vortex', 'Vow', 'Voyage', 'Wage', 'Winch', 'Wind', 'Wish',
]
MTG_COUNTERS = extend_all_cases(MTG_COUNTERS)
# now add +1/+1 etc counters, after the case expansion
# Note these all need to be fixed width for lookbehinds, so not an optimal expansion of a simple regex r'[\+\-]?\d+\/[\+\-]?\d+'
#   stop at 3 digits, probably nothing is bigger than that...
MTG_COUNTERS.extend([r'[\+\-]\d\/[\+\-]\d', r'\d\/[\+\-]\d', r'[\+\-]\d\/\d', r'\d\/\d',
                     r'[\+\-]\d\d\/[\+\-]\d\d', r'\d\d\/[\+\-]\d\d', r'[\+\-]\d\d\/\d\d', r'\d\d\/\d\d',
                     r'[\+\-]\d\d\d\/[\+\-]\d\d\d', r'\d\d\d\/[\+\-]\d\d\d', r'[\+\-]\d\d\d\/\d\d\d', r'\d\d\d\/\d\d\d',
                   ])

MTG_ABILITY_WORDS = ['Adamant', 'Addendum', 'Alliance', 'Battalion', 'Best in show', 'Bloodrush', 'Channel', 'Chroma', 'Cohort', 'Constellation', 'Converge',
                     'Council\'s dilemma', 'Coven', 'Crash Land', 'Delirium', 'Domain', 'Eminence', 'Enrage', 'Fateful hour', 'Ferocious', 'Formidable', 'Gear up',
                     'Gotcha!', 'Grandeur', 'Hellbent', 'Heroic', 'Imprint', 'Inspired', 'Join forces', 'Kinship', 'Landfall', 'Lieutenant', 'Magecraft',
                     'Metalcraft', 'Morbid', 'Pack tactics', 'Parade!', 'Parley', 'Radiance', 'Raid', 'Rally', 'Revolt', 'Spell mastery', 'Strive', 'Sweep',
                     'Tempting offer', 'Threshold', 'Underdog', 'Undergrowth', 'Will of the council',
]
MTG_ABILITY_WORDS = extend_all_cases(MTG_ABILITY_WORDS)

# mana costs are encoded as unique characters to reduce syntax burden on the AI, at the cost of increasing vocab
# as long as vocab doesn't go above 255 characters, it's not a significant impact to performance
# numerical mana is encoded differently (unary)
MTG_MANA_ENCODING = {
    '{1000000}' :                    ,  # special case, because we're not encoding that number in unary...
    '{100}'     :                    ,  # special case, because we're not encoding that number in unary...
    '{2/B}'     :                    ,  # Monocolored hybrid mana
    '{2/G}'     :                    ,  # Monocolored hybrid mana
    '{2/R}'     :                    ,  # Monocolored hybrid mana
    '{2/U}'     :                    ,  # Monocolored hybrid mana
    '{2/W}'     :                    ,  # Monocolored hybrid mana
    '{A}'       :                    ,  # Acorn counter
    '{B/G}'     :                    ,  # Hybrid mana
    '{B/P}'     :                    ,  # Phyrexian mana
    '{B/R}'     :                    ,  # Hybrid mana
    '{B}'       :                    ,  # Standard black mana
    '{CHAOS}'   :                    ,  # Chaos
    '{C}'       :                    ,  # Colorless only
    '{E}'       :                    ,  # Energy
    '{G/P}'     :                    ,  # Phyrexian mana
    '{G/U/P}'   :                    ,  # Phyrexian hybrid mana
    '{G/U}'     :                    ,  # Hybrid mana
    '{G/W/P}'   :                    ,  # Phyrexian hybrid mana
    '{G/W}'     :                    ,  # Hybrid mana
    '{G}'       :                    ,  # Standard green mana
    '{HR}'      :                    ,  # Half-red mana
    '{HW}'      :                    ,  # Half-white mana
    '{P}'       :                    ,  # Colorless Phyrexian mana
    '{Q}'       :                    ,  # Untap symbol
    '{R/G}'     :                    ,  # Hybrid mana
    '{R/P}'     :                    ,  # Phyrexian mana
    '{R/W}'     :                    ,  # Hybrid mana
    '{R}'       :                    ,  # Standard red mana
    '{S}'       :                    ,  # Snow
    '{TK}'      :                    ,  # Tokens
    '{T}'       :                    ,  # Tap symbol
    '{U/B}'     :                    ,  # Hybrid mana
    '{U/P}'     :                    ,  # Phyrexian mana
    '{U/R}'     :                    ,  # Hybrid mana
    '{U}'       :                    ,  # Standard blue mana
    '{W/B}'     :                    ,  # Hybrid mana
    '{W/P}'     :                    ,  # Phyrexian mana
    '{W/U}'     :                    ,  # Hybrid mana
    '{W}'       :                    ,  # Standard white mana
    '{X}'       :                    ,  # Variable 'X' mana
    '{Y}'       :                    ,  # Variable 'Y' mana
    '{Z}'       :                    ,  # Variable 'Z' mana
    '{½}'       :                    ,  # Half colorless mana
    '{∞}'       :                    ,  # infinity mana
}
MTG_MANA_DECODING = {v:k for k,v in MTG_MANA_ENCODING.items()}


def deduplicate_cards_simple(cards):
    # consumes list of internal formats, returns list of internal formats
    # drops identical copies of cards

    # for performance reasons, group cards by name, and down-select within each name group
    #   this produces identical results since the name field is compared anyway
    # each name group may contribute multiple down-selected cards
    #   and that is expected since some cards have been rebalanced, resulting in technical differences in important fields such as cost or main_text
    #   we are intentionally keeping each card with even slight variations
    # can't use a set to deduplicate because dict's aren't hashable
    groups = defaultdict(list)
    for card in cards:
        groups[card['name']].append(card)

    unique_cards = []
    for name, group in groups.items():
        unique_group = []
        for card in group:
            if card not in unique_group:
                unique_group.append(card)
        unique_cards.extend(unique_group)

    return unique_cards


def limit_to_AI_training_cards(cards):
    # consumes list of internal formats, returns list of internal formats
    # drops those cards which are not suitable for the AI to train with

    # TODO
    limited_cards = cards

    return limited_cards


def json_to_internal_format(json_path):
    # consumes AllPrintings.json, produces list of internally formated cards
    # deduplicates cards that repeat. See deduplicate_cards() for details
    # Docs for AllPrintings.json are located here: https://mtgjson.com/data-models/card-set/ etc
    #   we're iterating over 'Set' and then 'Card (Set)' objects, as defined by those docs

    f = open(json_path)
    j = json.load(f)
    f.close()

    cards = []

    for k_set, v_set in list(j['data'].items()):
        # collect set cards first, to make correct b-side associations
        # then add these to the aggregate set above
        primary_sides = []
        non_primary_sides = []

        # this is a big and complicated dataset, so lets make sure the list of available information matches our expectations
        expected_keys = ['baseSetSize', 'cards', 'code', 'isFoilOnly', 'isOnlineOnly', 'keyruneCode', 'name', 'releaseDate', 'tokens', 'totalSetSize',
                         'translations', 'type',
                        ]
        optional_keys = ['block', 'booster', 'cardsphereSetId', 'codeV3', 'isForeignOnly', 'isNonFoilOnly', 'isPaperOnly', 'isPartialPreview', 'mcmId',
                         'mcmIdExtras', 'mcmName', 'mtgoCode', 'parentCode', 'sealedProduct', 'tcgplayerGroupId',
                        ]
        for k in expected_keys: assert k in v_set, k
        for k in v_set: assert k in expected_keys or k in optional_keys, k

        for j_card in v_set['cards']:
            # this is a big and complicated dataset, so lets make sure the list of available information matches our expectations
            expected_keys = ['availability', 'borderColor', 'colorIdentity', 'colors', 'finishes', 'foreignData', 'frameVersion', 'identifiers', 'language',
                             'layout', 'legalities', 'manaValue', 'name', 'number', 'purchaseUrls', 'rarity', 'rulings', 'setCode', 'subtypes', 'supertypes',
                             'type', 'types', 'uuid',
                            ]
            deprecated_keys = ['convertedManaCost', 'hasFoil', 'hasNonFoil',]
            optional_keys = ['artist', 'asciiName', 'boosterTypes', 'cardParts', 'colorIndicator', 'edhrecRank', 'faceConvertedManaCost', 'faceFlavorName',
                             'faceManaValue', 'faceName', 'flavorName', 'flavorText', 'frameEffects', 'hand', 'hasAlternativeDeckLimit', 'hasContentWarning',
                             'isAlternative', 'isFullArt', 'isFunny', 'isOnlineOnly', 'isOversized', 'isPromo', 'isRebalanced', 'isReprint', 'isReserved',
                             'isStarter', 'isStorySpotlight', 'isTextless', 'isTimeshifted', 'keywords', 'leadershipSkills', 'life', 'loyalty', 'manaCost',
                             'originalPrintings', 'originalReleaseDate', 'originalText', 'originalType', 'otherFaceIds', 'power', 'printings', 'promoTypes',
                             'rebalancedPrintings', 'securityStamp', 'side', 'signature', 'text', 'toughness', 'variations', 'watermark',
                            ]
            undocumented_keys = ['attractionLights', 'duelDeck', 
                                ]
            for k in expected_keys: assert k in j_card, k + str(j_card)
            for k in j_card: assert k in expected_keys or k in deprecated_keys or k in optional_keys or k in undocumented_keys, k + str(j_card)

            # create a backlink from the card object to its set
            j_card['set'] = v_set

            # write card fields
            # json_fields is a temporary field which will be removed at the end of this process
            card = {'json_fields': j_card}

            # name
            if 'faceName' in j_card:
                card['name'] = j_card['faceName']
            else:
                card['name'] = j_card['name']

            # main_text. json property 'isTextless' is sometimes not correct, so don't use it
            if 'text' in j_card:
                card['main_text'] = j_card['text']
            elif 'originalText' in j_card:
                card['main_text'] = j_card['originalText']
            else:
                card['main_text'] = None
            card['main_text'] = card['main_text'] or None  # handle empty strings, if any

            # cost
            if 'manaCost' in j_card:
                card['cost'] = j_card['manaCost']
            else:
                card['cost'] = None

            # power_toughness
            assert (('power' in j_card and 'toughness' in j_card)
                 or ('power' not in j_card and 'toughness' not in j_card))
            if 'power' in j_card:
                card['power_toughness'] = [j_card['power'],
                                           j_card['toughness']]
            else:
                card['power_toughness'] = None

            # loyalty
            if 'loyalty' in j_card:
                card['loyalty'] = j_card['loyalty']
            else:
                card['loyalty'] = None

            # flavor
            if 'flavorText' in j_card:
                card['flavor'] = j_card['flavorText']
            else:
                card['flavor'] = None
            
            # rarity
            card['rarity'] = j_card['rarity']

            # types
            card['maintypes'] = j_card['types']
            card['subtypes'] = j_card['subtypes']
            card['supertypes'] = j_card['supertypes']

            # assign as primary or non-primary card sides. Non-primary card sides will be sorted into their primaries later
            if 'side' in j_card and j_card['side'] in ['b', 'c', 'd', 'e']:
                assert 'otherFaceIds' in j_card
                non_primary_sides.append(card)
            else:
                primary_sides.append(card)

        # assign non_primary_sides to their primary side
        for np_card in non_primary_sides:
            for p_card in primary_sides:
                if p_card['json_fields']['uuid'] in np_card['json_fields']['otherFaceIds']:
                    p_card[np_card['json_fields']['side'] + '_side'] = np_card
                    break
            else:
                raise ValueError(f"Primary card not found for \"{np_card['name']}\" {np_card['json_fields']['uuid']}")

        # populate num_sides field
        for card in primary_sides:
            num_sides = 1
            if 'b_side' in card: num_sides += 1
            if 'c_side' in card: num_sides += 1
            if 'd_side' in card: num_sides += 1
            if 'e_side' in card: num_sides += 1
            card['num_sides'] = num_sides

        # finally, remove the json_fields temporary key
        for card in primary_sides:
            del card['json_fields']
            if 'b_side' in card: del card['b_side']['json_fields']
            if 'c_side' in card: del card['c_side']['json_fields']
            if 'd_side' in card: del card['d_side']['json_fields']
            if 'e_side' in card: del card['e_side']['json_fields']

        cards.extend(primary_sides)

    return cards


def AI_to_internal_format(AI_string):
    # consumes a single AI formatted string, produces a single internally formatted card
    # runs error correction, parsing, and validation before returning the card
    # may raise errors during validation

    AI_string = error_correct_AI(AI_string)
    
    # TODO
    pass

    validate(card)
    return card


def internal_format_to_AI_format(card):
    # consumes list of internal formats, returns list of internal formats
    # consumes a single internal format, produces a single AI formatted string
    # TODO

    # TODO
    # convert all fields to lowercase
    #   except mana costs
    #   and except variable usage of X
    #     'cost'            : str or None
    #     'flavor'          : str or None
    #     'loyalty'         : str or None
    #     'main_text'       : str
    #     'maintypes'       : list of str (possibly empty)
    #     'name'            : str
    #     'num_sides'       : int (1-5), optional, present only on a-side (top-level) cards
    #     'power_toughness' : 2-list of str or None
    #     'rarity'          : str
    #     'subtypes'        : list of str (possibly empty)
    #     'supertypes'      : list of str (possibly empty)

    # standardize verbiage for countering spells to "uncast"
    #   this reduces overloading of the word "counter" for the AI
    # assume all uses of "counter" outside the list of MTG_COUNTERS is a verb
    main_text = card['main_text']
    main_text = re.sub(rf'(?<!{" )(?<!".join(MTG_COUNTERS)} )counter', 'uncast', main_text)
    main_text = re.sub(rf'(?<!{" )(?<!".join(MTG_COUNTERS)} )Counter', 'Uncast', main_text)

    # name_val = name_val.lower()

    # text_val = src_json['text'].lower()
    # text_val = transforms.text_pass_2_cardname(text_val, name_orig)
    # text_val = transforms.text_pass_3_unary(text_val)
    # text_val = transforms.text_pass_4a_dashes(text_val)
    # text_val = transforms.text_pass_5_counters(text_val)
    # text_val = transforms.text_pass_7_choice(text_val)
    # text_val = transforms.text_pass_9_newlines(text_val)
    # text_val = transforms.text_pass_10_symbols(text_val)

    # TODO recurse on b-e sides

    pass


def validate(card):
    # consumes internal format, raises error on validation fail
    # should not raise error for all canonical cards, but may raise errors for AI generated cards
    
    # check that X has a definition if it is present anywhere

    # check that counters have a type definition (or are generic counters allowed?)

    # check that the only numbers that exist are 
    pass  # TODO


def error_correct_AI(AI_string):
    # consumes AI format, returns AI format with error corrections applied
    # OR maybe consumes internal format, returns internal format with error corrections applied
    pass  # TODO


def unreversable_modifications(card):
    # consumes a single internal format, modifies it in place
    # makes changes which are not reversable by AI_to_internal_format
    #   such as stripping and enforcing repeatable capitalization
    # this function will return a dataset which can be directly compared to the dual_processed format for validity
    # since the changes made by this function are not validated by reversion, they should be reviewed by hand

    # strip text fields
    card['name'] = card['name'].strip()
    if card['main_text'] is not None:
        card['main_text'] = card['main_text'].strip()
    if card['flavor'] is not None:
        card['flavor'] = card['flavor'].strip()

    # fix alchemy symbol prepended to card names
    card['name'] = re.sub(r'^A-', '', card['name'])

    # convert one-off large nubmers to strings, since numbers are reserved characters
    # normal (smaller) numbers will be converted to unary, but that doesn't make sense for these
    # there also aren't very many number above 20 actually used
    def sub_large_numbers(s):
        s = re.sub('100,?000', 'one-hundred-thousand', s)
        s = re.sub('1,?996', 'nineteen-ninety-six', s)  # date instead of amount?
        s = re.sub('1,?000', 'one-thousand', s)
        s = s.replace('200', 'two-hundred')
        s = s.replace('100', 'one-hundred')
        s = s.replace('50', 'fifly')
        s = s.replace('40', 'forty')
        s = s.replace('30', 'thirty')
        s = s.replace('25', 'twenty-five')
        return s

    card['name'] = sub_large_numbers(card['name'])
    if card['main_text'] is not None:
        card['main_text'] = sub_large_numbers(card['main_text'])

    # convert common unicode characters to ascii, both for standardization for the AI, and to reduce vocab size
    # a few of these characters are intentionally commented out, we specifically want those unicode characters to remain
    #   bullet: needs a unique replacement character anyway, so might as well use an actual bullet
    #   1/2: avoid overloading the meaning of numbers or '/' character for the AI
    #   inf: 
    def sub_unicode(s):
        s = s.replace('\u2014', '-')    # long dash
        # s = s.replace('\u2022': '*')  # bullet
        s = s.replace('\u2019', '"')    # single quote
        s = s.replace('\u2018', '"')    # another single quote
        s = s.replace('\u2212', '-')    # minus sign
        s = s.replace('\xe6',   'ae')   # ae symbol
        s = s.replace('\xfb',   'u')    # u with caret
        s = s.replace('\xfa',   'u')    # u with accent
        s = s.replace('\xe9',   'e')    # e with accent
        s = s.replace('\xe1',   'a')    # a with accent
        s = s.replace('\xe0',   'a')    # a with accent going the other way
        s = s.replace('\xe2',   'a')    # a with caret
        s = s.replace('\xf6',   'o')    # o with umlaut
        s = s.replace('\xed',   'i')    # i with accent
        s = s.replace('\u03c0', 'pi')   # pi
        s = s.replace('\xae',   'r')    # Registered trademark as r
        # s = s.replace('\xbd',   '1/2')  # 1/2
        # s = s.replace('\u221e', 'inf')  # infinity
        s = s.replace('\u2610', 'na')   # ballot box as na
        return s

    card['name'] = sub_unicode(card['name'])
    if card['main_text'] is not None:
        card['main_text'] = sub_unicode(card['main_text'])
    if card['flavor'] is not None:
        card['flavor'] = sub_unicode(card['flavor'])

    if card['main_text'] is not None:
        # remove rules (keyword explanation) text
        card['main_text'] = re.sub(r'\(.*\)', '', card['main_text'])  # this makes a pretty big assumption, which is hard to verify...

        # remove ability words, which thematically groups cards with a common functionality, but have no actual rules meaning
        card['main_text'] = re.sub(rf'({"|".join(MTG_ABILITY_WORDS)})\s*-?\s*', '', card['main_text'])

        # Capitalize all X's, Y's, and Z's, when acting as variables
        variable_x_regex = r'((?<=^)|(?<=[\s\+\-\/\{]))([xXyYzZ])(?=$|[\s:,\.\/\}])'
        capitalize = lambda x: x.group(2).upper()
        card['main_text'] = re.sub(variable_x_regex, capitalize, card['main_text'])

        # TODO maybe?
        # text_val = transforms.text_pass_8_equip(text_val)
        #   careful about things like this "Equip Shaman, Warlock, or Wizard {1}"
        # text_val = transforms.text_pass_11_linetrans(text_val)  # standardize order of keywords

        # remove trailing whitespace on a line, and remove blank lines, which might for instance by introduced by the above
        # don't remove leading whitespace, which might be intentional formatting
        card['main_text'] = re.sub(r'\s+(?=\n|$)', '', card['main_text'])

    # apply strict titlecasing to the card name
    # this gives us a robust target for the AI to internal decoder, since the AI text is all lowercase
    # apply the exact same transformation to the card name when found in the main text
    #   since references to card title are encoded to special characters in the AI format, and we need to be able to find them later
    new_name = titlecase.titlecase(card['name'].lower())  # lower() call ensures titlecaser doesn't try to get too smart about acronym capitalization
    if card['main_text'] is not None:
        segments = re.split(fr"({re.escape(card['name'])})", card['main_text'])
        segments = list(segments)
        for i_segment, segment in enumerate(segments):
            if segment == card['name']:
                segments[i_segment] = new_name
        card['main_text'] = ''.join(segments)
    card['name'] = new_name

    # recurse on b-e sides
    if 'b_side' in card:
        card['b_side'] = unreversable_modifications(card['b_side'])
    if 'c_side' in card:
        card['c_side'] = unreversable_modifications(card['c_side'])
    if 'd_side' in card:
        card['d_side'] = unreversable_modifications(card['d_side'])
    if 'e_side' in card:
        card['e_side'] = unreversable_modifications(card['e_side'])

    return card


def verify_decoder_reverses_encoder(cards_limited_standard, cards_dual_processed):
    # this helps validate that both the encoder and decorder are working properly, or at least have symmetric bugs
    # consumes two lists of internally formatted cards, and compares them
    # if the two are not equal, raises error
    # this is only executed during encode_json_to_AI
    #   and is a test of the program design over the space of the cards from AllPrintings.json
    #   this does not process any AI generated data
    pass  # TODO


def encode_json_to_AI(json_path, out_path):
    # consumes AllPrintings.json
    # runs through encoding and decoding steps
    #   comapares encoded+decoded dataset to original dataset for end-to-end validity checking
    # produces several local data files for human comparison / debugging if validation fails
    # saves encoded data file to designated location

    cards = json_to_internal_format(json_path)
    for card in cards:
        validate(card)

    # perform dataset modifications / standardizations which have no reverse
    cards = [unreversable_modifications(card) for card in cards]

    # deduplicate the cards
    # We do this after standardization due to some unfortunate artifacts in the json fields, which are addressed in that step
    cards = deduplicate_cards_simple(cards)

    # limit dataset to those cards upon which the AI should train
    cards = limit_to_AI_training_cards(cards)

    # transcribe to AI format, and save in designated location
    cards_AI = [internal_format_to_AI_format(card) for card in cards]
    f = open(out_path, 'w')  # TODO use byte encoding to prevent unintended OS transcriptions?
    f.write('\n'.join(cards_AI))
    f.close()

    # decode AI format back to internal format, and then compare to the limited dataset from above
    cards_dual_processed = [AI_to_internal_format(card) for card in cards_AI]
    verify_decoder_reverses_encoder(cards_limited_standard, cards_dual_processed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_path", type=str, help="path to names AllPrintings.json")
    parser.add_argument("--out_path", type=str, help="path to output file")
    args = parser.parse_args()

    encode_json_to_AI(args.json_path, args.out_path)

