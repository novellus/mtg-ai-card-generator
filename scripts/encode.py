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
#     'json_fields'     : dict, optional, only exists if the card was converted from json,
#                         contains select unmodified fields used in decision making (eg which cards should be encoded)
#     'loyalty'         : str or None
#     'main_text'       : str
#     'maintypes'       : list of str (possibly empty)
#     'name'            : str
#     'num_sides'       : int (1-5)
#     'power_toughness' : 2-list of str or None
#     'rarity'          : str
#     'subtypes'        : list of str (possibly empty)
#     'supertypes'      : list of str (possibly empty)
# }


def deduplicate_cards(cards):
    # consumes list of internal formats, returns list of internal formats
    # drops duplicate cards, such as reprints, foils, etc
    # TODO
    pass


def limit_to_AI_training_cards(cards):
    # consumes list of internal formats, returns list of internal formats
    # drops those cards which are not suitable for the AI to train with
    # TODO
    pass


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

            # TODO write card fields
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

        cards.extend(primary_sides)

    return cards


def AI_to_internal_format(AI_string):
    # consumes a single AI formatted string, produces a single internally formatted card
    # runs error correction, parsing, and validation before returning the card
    # may raise errors during validation

    AI_string = error_correct_AI(AI_string)
    
    # TODO

    validate(card)
    return card


def internal_format_to_human_readable(cards, out_path):
    # consumes a list of internally formatted cards, produces a yaml file
    pass  # TODO


def internal_format_to_AI_format(card):
    # consumes list of internal formats, returns list of internal formats
    # consumes a single internal format, produces a single AI formatted string
    # TODO

    # s = s.replace('-', dash_marker)
    # name_val = name_val.lower()

    # text_val = src_json['text'].lower()
    # text_val = transforms.text_pass_2_cardname(text_val, name_orig)
    # text_val = transforms.text_pass_3_unary(text_val)
    # text_val = transforms.text_pass_4a_dashes(text_val)
    # text_val = transforms.text_pass_5_counters(text_val)
    # text_val = transforms.text_pass_7_choice(text_val)
    # text_val = transforms.text_pass_9_newlines(text_val)
    # text_val = transforms.text_pass_10_symbols(text_val)

    pass


def limit_to_AI_fields(card):
    # consumes list of internal formats, returns list of internal formats including only the fields which the AI processes
    # used to produce a limited dataset for direct comparison after the AI processing
    pass  # TODO


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


def unreversable_modifications(cards):
    # consumes list of internal formats, returns list of internal formats
    # makes changes which are not reversable by AI_to_internal_format
    #   such as standardizing order of keywords
    # this function will return a dataset which can be directly compared to the dual_processed format for validity
    # since the changes made by this function are not validated by reversion, they should be reviewed by hand
    # TODO

    cards = copy.deepcopy(cards)
    for card in cards:

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
        def sub_unicode(s):
            # TODO check if we 
            s = s.replace('\u2014', '-')    # unicode long dash
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
            s = s.replace('\xbd',   '1/2')  # 1/2 unicode to string
            s = s.replace('\u221e', 'inf')  # infinity
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
            # TODO check capitalization
            ability_words = ['Adamant', 'Addendum', 'Alliance', 'Battalion', 'Best in show', 'Bloodrush', 'Channel', 'Chroma', 'Cohort', 'Constellation',
                             'Converge', 'Council\'s dilemma', 'Coven', 'Crash Land', 'Delirium', 'Domain', 'Eminence', 'Enrage', 'Fateful hour', 'Ferocious',
                             'Formidable', 'Gear up', 'Gotcha!', 'Grandeur', 'Hellbent', 'Heroic', 'Imprint', 'Inspired', 'Join forces', 'Kinship', 'Landfall',
                             'Lieutenant', 'Magecraft', 'Metalcraft', 'Morbid', 'Pack tactics', 'Parade!', 'Parley', 'Radiance', 'Raid', 'Rally', 'Revolt',
                             'Spell mastery', 'Strive', 'Sweep', 'Tempting offer', 'Threshold', 'Underdog', 'Undergrowth', 'Will of the council',]
            card['main_text'] = re.sub(rf'({"|".join(ability_words)})\s*-?\s*', '', card['main_text'])

            # text_val = transforms.text_pass_4b_x(text_val)
            # text_val = transforms.text_pass_6_uncast(text_val)
            # text_val = transforms.text_pass_8_equip(text_val)
            # text_val = transforms.text_pass_11_linetrans(text_val)  # standardize order of keywords

        # TODO
        # apply strict titlecasing to the card name
        # this gives us a robust target for the AI to internal decoder, since the AI text is all lowercase
        # apply the exact same transformation to the card name when found in the main text
        #   since references to card title are encoded to special characters in the AI format, and we need to be able to find them later

        # TODO recurse on b-e sides

    return cards



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

    cards_original = json_to_internal_format(json_path)
    for card in cards_original:
        validate(card)

    # save an unmodified dataset for human review
    # internal_format_to_human_readable(cards_original, 'cards_original.yaml')

    # perform dataset modifications / standardizations which have no reverse
    cards_standard = unreversable_modifications(cards_original)

    # now deduplicate the cards
    # We do this after standardization due to some unfortunate artifacts in the json fields, which are addressed in that step
    cards_original = deduplicate_cards(cards_original)

    # save the standardized dataset for human review
    # internal_format_to_human_readable(cards_standard, 'cards_standard.yaml')
    cards_limited_standard = limit_to_AI_fields(cards_standard)
    # internal_format_to_human_readable(cards_limited_standard, 'cards_limited_standard.yaml')

    # transcribe to AI format, and save in designated location
    cards_AI = []
    for card in cards_original:
        cards_AI.append(internal_format_to_AI_format(card))
    f = open(out_path, 'w')  # TODO use byte encoding to prevent unintended OS transcriptions?
    f.write('\n'.join(cards_AI))
    f.close()

    # decode AI format back to internal format for error checking
    cards_dual_processed = []  # TODO get a better name for this
    for card in cards_AI:
        cards_dual_processed.append(AI_to_internal_format(card))

    # save cards_dual_processed for human review
    # internal_format_to_human_readable(cards_dual_processed, 'cards_dual_processed.yaml')

    verify_decoder_reverses_encoder(cards_limited_standard, cards_dual_processed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_path", type=str, help="path to names AllPrintings.json")
    parser.add_argument("--out_path", type=str, help="path to output file")
    args = parser.parse_args()

    encode_json_to_AI(args.json_path, args.out_path)

