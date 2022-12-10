import argparse
import json

from collections import defaultdict


# internally formatted cards have the following fields. All fields are always present except those indicated as optional
# {
#     'a_side'          : internal format, optional, links to parent, present only on b-, c-, d-, and e- side cards
#     'b_side'          : internal format, optional, present only on a-side (top-level) cards
#     'c_side'          : internal format, optional, present only on a-side (top-level) cards
#     'cost'            : str or None
#     'd_side'          : internal format, optional, present only on a-side (top-level) cards
#     'e_side'          : internal format, optional, present only on a-side (top-level) cards
#     'json_fields'     : dict, optional, only exists if the card was converted from json,
#                         contains select unmodified fields used in decision making (eg which cards should be encoded)
#     'loyalty'         : int or None
#     'main_text'       : str
#     'maintypes'       : list of str (possibly empty)
#     'name'            : str
#     'num_sides'       : int (1-5)
#     'power_toughness' : 2-list of int or None
#     'rarity'          : str
#     'subtypes'        : list of str (possibly empty)
#     'supertypes'      : list of str (possibly empty)
#     'unparsed_name'   : str
# }


def deduplicate_cards(card_duplicates):
    # TODO
    pass


def limit_to_AI_training_cards(cards):
    # consumes list of internal formats, returns list of internal formats
    # drops those cards which are not suitable for the AI to train with
    # TODO
    pass


def json_to_internal_format(json_path):
    # consumes AllPrintings.json, produces list of internally formated cards
    # Docs for AllPrintings.json are located here: https://mtgjson.com/data-models/card-set/ etc
    #   we're iterating over 'Set' and then 'Card (Set)' objects, as defined by those docs
    f = open(json_path)
    j = json.load(f)
    f.close()

    # collect all cards, storing duplicates as lists by resolved name
    card_duplicates = defaultdict(list)  # name: [card, card, card]
    for k_set, v_set in list(j['data'].items()):
        # collect set cards first, to make correct b-side associations
        # then add these to the aggregate set above
        set_cards = defaultdict(list)
        b_sides = []  # TODO sides go up to 'e'...

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

            card = {}
            # TODO write card fields

            set_cards[card['name']].append(card)  # TODO: or assign to b-sides

    # then deduplicate by choosing # TODO attributes

    # return cards


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
    # consumes a single internal format, produces a single AI formatted string
    pass  # TODO


def limit_to_AI_fields(card):
    # consumes a single internal format, returns internal format including only the fields which the AI processes
    # used to produce a limited dataset for direct comparison after the AI processing
    pass  # TODO


def validate(card):
    # consumes internal format, raises error on validation fail
    # should not raise error for all canonical cards, but may raise errors for AI generated cards
    # for instance, check that X has a definition if it is present anywhere
    pass  # TODO


def error_correct_AI(AI_string):
    # consumes AI format, returns AI format with error corrections applied
    # OR maybe consumes internal format, returns internal format with error corrections applied
    pass  # TODO


def unreversable_modifications(card):
    # consumes a single internal format, produces a single internal format
    # makes changes which are not reversable by AI_to_internal_format
    # this function will return the dataset which can be directly compared to the dual_processed format for validity
    #   such as standardizing order of keywords
    # since the changes made by this function are not validated by reversion, they should be reviewed by hand
    pass  # TODO


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
    internal_format_to_human_readable(cards_original, 'cards_original.yaml')

    # perform dataset modifications / standardizations which have no reverse
    cards_standard = []
    for card in cards_original:
        cards_standard.append(unreversable_modifications(card))

    # save the standardized dataset for human review
    internal_format_to_human_readable(cards_standard, 'cards_standard.yaml')
    cards_limited_standard = limit_to_AI_fields(cards_original)
    internal_format_to_human_readable(cards_limited_standard, 'cards_limited_standard.yaml')

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
    internal_format_to_human_readable(cards_dual_processed, 'cards_dual_processed.yaml')

    verify_decoder_reverses_encoder(cards_limited_standard, cards_dual_processed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_path", type=str, help="path to names AllPrintings.json")
    parser.add_argument("--out_path", type=str, help="path to output file")
    args = parser.parse_args()

    encode_json_to_AI(args.json_path, args.out_path)

