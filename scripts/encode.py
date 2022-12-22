import argparse
import copy
import difflib
import json
import itertools
import pprint
import re
import sys
import titlecase

from mtg_constants import *

from collections import defaultdict
from collections import namedtuple


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
#     'main_text'       : str or None
#     'type'            : str
#     'name'            : str
#     'power_toughness' : 2-list of str or None
#     'rarity'          : str
# }


def XYZ_variable_capitalize(s):
    # Capitalize all X's, Y's, and Z's, when acting as variables
    variable_x_regex = r'((?<=^)|(?<=[\s\+\-\/\{]))([xXyYzZ])(?=$|[\s:,\.\/\}])'
    capitalize = lambda x: x.group(2).upper()
    return re.sub(variable_x_regex, capitalize, s)


def deduplicate_cards(cards):
    # consumes list of internal formats, returns list of internal formats
    # drops identical copies of cards
    # omits rarity in compared fields
    #   In the case that rarity is the only distinction between two cards, arbitrarily picks the first one in the input list

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
            card_restricted = {k:v for k,v in card.items() if k not in ['rarity']}
            if card_restricted not in unique_group:
                unique_group.append(card_restricted)
                unique_cards.append(card)

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
            card['type'] = j_card['type']

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

        # verify b-e sides don't skip letters (always in order)
        for card in primary_sides:
            if 'c_side' in card: assert 'b_side' in card 
            if 'd_side' in card: assert 'c_side' in card 
            if 'e_side' in card: assert 'd_side' in card 

        # finally, remove the json_fields temporary key
        for card in primary_sides:
            del card['json_fields']
            if 'b_side' in card: del card['b_side']['json_fields']
            if 'c_side' in card: del card['c_side']['json_fields']
            if 'd_side' in card: del card['d_side']['json_fields']
            if 'e_side' in card: del card['e_side']['json_fields']

        cards.extend(primary_sides)

    return cards


def pairs(x):
    # returns list of pairs of elements of x with no repeats
    #   eg [(x[0], x[1]), (x[2], x[3]), ...]

    for i, y in enumerate(itertools.pairwise(x)):
        # drop the odd yields from itertools.pairwise
        if i%2:
            continue

        yield y


def decimal_to_unary(s, mana=False):
    # s is string of decimal encoded integer
    # returns string of unary encoded integer

    if mana:
        prefix = '⓿'
    else:
        prefix = '⓪'

    # handle leading zeros
    if s[0] == '0' and len(s) > 1:
        return prefix + decimal_to_unary(s[1:], mana=mana)

    return prefix + '^' * int(s)


def unary_to_decimal(s):
    # s is string of unary encoded integer
    # returns string of decimal encoded integer

    return str(len(s))


class Number_Word_Converter():
    # converts number words to / from integers
    # eg '37' <-> 'thirty seven'

    def __init__(self):
        self._units = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
                  'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
                  'sixteen', 'seventeen', 'eighteen', 'nineteen',
        ]
        self._tens = ['twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
        self._scales = ['hundred', 'thousand', 'million', 'billion', 'trillion']

        self.NUMBER_WORDS = self._units + self._tens + self._scales

        self._multiply = {}
        self._increment = {}

        for i_word, word in enumerate(self._units):
            self._increment[word] = i_word

        for i_word, word in enumerate(self._tens):
            self._increment[word] = (i_word + 2) * 10

        for i_word, word in enumerate(self._scales):
            if i_word == 0:
                self._multiply[word] = 10 ** 2
            else:
                self._multiply[word] = 10 ** (i_word * 3)

    def str_to_int(self, s):
        # eg 'thirty seven' -> '37'

        total = 0
        intermediate = 0
        for word in re.split(r'[ \-]', s.strip()):
            assert word in self.NUMBER_WORDS or word == 'and', 'Not a supported number word: ' + word

            multiply = self._multiply.get(word, 1)
            increment = self._increment.get(word, 0)
            intermediate = intermediate * multiply + increment

            if multiply > 100:
                total += intermediate
                intermediate = 0

        return str(total + intermediate)

    def int_to_str(s):
        # eg '37' -> 'thirty seven'

        s = str(s)  # allow actual integers as input
        l = len(s)

        words = []
        digits = ''
        for i_char, char in enumerate(s):
            reverse_i_char = l - i_char - 1

            scale = None
            if reverse_i_char > 2:
                scale = scales[reverse_i_char // 3]

            terminates_scale = not reverse_i_char % 3

            if not terminates_scale:
                digits += char

            else:
                if len(digits) == 3:
                    words.append(self._units[int(digits[0])])
                    words.append(self._scales[0])
                    digits = digits[1:]

                if int(digits) < 20:
                    words.append(self._units[int(digits)])
                else:
                    words.append(self._tens[int(digits[0] - 2)])
                    words.append(self._units[int(digits[1])])

                if scale is not None:
                    words.append(self._scales[scale])

                digits = ''

        return ' '.join(words)


nwc = Number_Word_Converter()


def internal_format_to_AI_format(card):
    # consumes list of internal formats, returns list of internal formats
    # consumes a single internal format, produces a single AI formatted string

    # convert fields to local variables, specifically do not edit input dict
    # add default values for AI fields when card fields are None
    cost            = card['cost'] or ''
    loyalty         = card['loyalty'] or ''
    main_text       = card['main_text'] or ''
    type_string     = card['type']
    name            = card['name']
    power_toughness = card['power_toughness'] or []
    rarity          = card['rarity']

    # encode rarity as unique symbols
    rarity = MTG_RARITY_JSON_TO_AI_FORMAT[rarity]

    # str encode the power and toughness
    power_toughness = '/'.join(power_toughness)

    # substitute card name with a unique character in main text so that there's only one copy of the full name for the AI to handle
    # skip this step if the card name is exactly equal to a reserved word / phrase
    # note this step is actually kinda difficult to get right, since
    #   keywords can be a subset of the name
    #   the name can be a subset of a keyword
    #   the name can be exactly a keyword (eg card named "Fear" uses keyword "Fear")
    #   so preventing accidental replacements of keywords while also replacing all names is difficult to verify
    if name not in MTG_KEYWORDS + MTG_TYPE_WORDS:
        main_text = main_text.replace(name, '@')

    # convert all fields to lowercase
    #   except mana costs
    #   and except variable usage of X, Y, and Z
    # Actually, getting correct capitalization in the reverse function is very difficult
    #   we can capitalize instances of the card name just fine, and characters beginning a sentence, after colons, etc
    #   but the hard part is made up proper names, partial name matches, types (usually), keywords (sometimes)
    #   the linguistical parsing is actually a fairly tough problem
    #   so we should let the AI handle capitialization entirely. It'll probably do better than we can
    # main_text = main_text.lower()
    # main_text = XYZ_variable_capitalize(main_text)
    # type_string = type_string.lower()
    # name = name.lower()
    # power_toughness = power_toughness.lower()

    # reduce character overloading for dashes
    # convert numerical minus signs to a unique character
    main_text = re.sub(r'(?<!\w)-(?=\d)', '∓', main_text)

    # encode symbols (including mana, excepting numerical) in AI format
    for a, b in MTG_SYMBOL_JSON_TO_AI_FORMAT.items():
        main_text = main_text.replace(a, b)
        cost = cost.replace(a, b)

    # encode numbers (including numerical mana) in every field to unary
    # mana
    cost = re.sub(r'\{(\d+)\}', lambda x: decimal_to_unary(x.group(1), mana=True), cost)
    main_text = re.sub(r'\{(\d+)\}', lambda x: decimal_to_unary(x.group(1), mana=True), main_text)
    # all remaining numbers
    name = re.sub(r'(\d+)', lambda x: decimal_to_unary(x.group(1)), name)
    loyalty = re.sub(r'(\d+)', lambda x: decimal_to_unary(x.group(1)), loyalty)
    main_text = re.sub(r'(\d+)', lambda x: decimal_to_unary(x.group(1)), main_text)
    power_toughness = re.sub(r'(\d+)', lambda x: decimal_to_unary(x.group(1)), power_toughness)

    # simplify repeated counter syntax, so the AI doesn't have to remember types once it specifies one
    # for each new counter type, encode it as 'type%'
    # repeated counters of the same type will be encoded simply as '%'
    reserved_char = '\u2014'  # we know this won't exist in the text when this function is used
    regex = fr'(?:(?<=^)|(?<=\W))({"|".join(MTG_COUNTERS)}) counter(?=$|\W)'
    subs = re.findall(regex, main_text)
    main_text = re.sub(regex, reserved_char, main_text)
    previous_counter = None
    for counter_type in subs:
        if counter_type == previous_counter:
            enc = '%'
        else:
            enc = f'{counter_type}%'
        main_text = main_text.replace(reserved_char, enc, 1)
        previous_counter = counter_type

    # standardize verbiage for countering spells to "uncast"
    #   this reduces overloading of the word "counter" for the AI
    # assume all uses of "counter" outside the list of MTG_COUNTERS is a verb
    main_text = re.sub(rf'(?<!{" )(?<!".join(MTG_COUNTERS)} )counter', 'uncast', main_text)
    main_text = re.sub(rf'(?<!{" )(?<!".join(MTG_COUNTERS)} )Counter', 'Uncast', main_text)

    # convert newlines to a unique character
    # we're going to reserve actual newlines for making the output file a bit more human readable
    main_text = main_text.replace('\n', '\\')

    # label fields for the AI
    #   this increases syntax, but regularizes AI output, so is a net win
    AI_string = f'{name}∥1{cost}∥2{type_string}∥3{loyalty}∥4{power_toughness}∥5{rarity}∥6{main_text}'

    # recurse on b-e sides
    if 'b_side' in card:
        AI_string += '␥' + internal_format_to_AI_format(card['b_side'])
    if 'c_side' in card:
        AI_string += '␥' + internal_format_to_AI_format(card['c_side'])
    if 'd_side' in card:
        AI_string += '␥' + internal_format_to_AI_format(card['d_side'])
    if 'e_side' in card:
        AI_string += '␥' + internal_format_to_AI_format(card['e_side'])

    return AI_string


def AI_to_internal_format(AI_string):
    # consumes a single AI formatted string, produces a single internally formatted card
    # runs error correction, parsing, and validation before returning the card
    # may raise errors during validation

    AI_string = error_correct_AI(AI_string)

    sides = AI_string.split('␥')
    assert sides

    # breakup fields
    card = {}
    fields = re.split(r'(∥\d)', sides[0])
    card['name'] = fields[0]

    field_names = {'∥1': 'cost', '∥2': 'type', '∥3': 'loyalty', '∥4': 'power_toughness', '∥5': 'rarity', '∥6': 'main_text'}
    for field_id, field in pairs(fields[1:]):
        field_name = field_names[field_id]
        card[field_name] = field

    for k, v in field_names.items():
        assert v in card, f'Failed to find field "{v}" in "{AI_string}" -> {fields}'

    # decode newlines
    card['main_text'] = card['main_text'].replace('\\', '\n')

    # decode rarity
    card['rarity'] = MTG_RARITY_AI_TO_JSON_FORMAT[card['rarity']]

    # revert uncast to counter
    card['main_text'] = card['main_text'].replace('uncast', 'counter')
    card['main_text'] = card['main_text'].replace('Uncast', 'Counter')

    # decode counter syntax to human readable format
    reserved_char = '\u2014'  # we know this won't exist in the text when this function is used
    regex = r'(\S*)%'
    subs = re.findall(regex, card['main_text'])
    card['main_text'] = re.sub(regex, reserved_char, card['main_text'])
    counter_type = None
    for new_type in subs:
        counter_type = new_type or counter_type
        assert counter_type is not None, card['main_text']  # don't let the AI not label the first counter
        card['main_text'] = card['main_text'].replace(reserved_char, f'{counter_type} counter', 1)

    # decode symbols (including mana, excepting numerical)
    for a, b in MTG_SYMBOL_AI_TO_JSON_FORMAT.items():
        card['main_text'] = card['main_text'].replace(a, b)

    for a, b in MTG_SYMBOL_AI_TO_JSON_FORMAT.items():
        card['cost'] = card['cost'].replace(a, b)

    # decode numbers (including numerical mana) in every field from unary
    # mana
    card['cost'] = re.sub(r'⓿(\^*)', lambda x: '{' + unary_to_decimal(x.group(1)) + '}', card['cost'])
    card['main_text'] = re.sub(r'⓿(\^*)', lambda x: '{' + unary_to_decimal(x.group(1)) + '}', card['main_text'])
    # all remaining numbers
    card['name'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['name'])
    card['loyalty'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['loyalty'])
    card['main_text'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['main_text'])
    card['power_toughness'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['power_toughness'])

    # reduce character overloading for dashes
    # convert numerical minus signs to a unique character
    card['main_text'] = re.sub(r'∓', '-', card['main_text'])

    # decode power toughness
    if card['power_toughness'] != '':
        card['power_toughness'] = card['power_toughness'].split('/')

    # replace backreferences to name
    card['main_text'] = card['main_text'].replace('@', card['name'])

    # insert None values instead of empty strings
    card['cost'] = card['cost'] or None
    card['loyalty'] = card['loyalty'] or None
    card['power_toughness'] = card['power_toughness'] or None
    card['main_text'] = card['main_text'] or None

    # recurse on b-e sides
    if len(sides) >= 2: card['b_side'] = AI_to_internal_format(sides[1])
    if len(sides) >= 3: card['c_side'] = AI_to_internal_format(sides[2])
    if len(sides) >= 4: card['d_side'] = AI_to_internal_format(sides[3])
    if len(sides) >= 5: card['e_side'] = AI_to_internal_format(sides[4])
    if len(sides) > 5:
        raise NotImplementedError('Too many sides, only implemented a-e sides')
    
    validate(card)
    return card


def validate(card):
    # consumes internal format, raises error on validation fail
    # should not raise error for all canonical cards, but may raise errors for AI generated cards
    
    # check that X has a definition if it is present anywhere

    pass  # TODO


def error_correct_AI(AI_string):
    # consumes AI format, returns AI format with error corrections applied
    #   OR maybe consumes internal format, returns internal format with error corrections applied
    # Don't need to check validity of implicitely checked attributes
    #   such as checking that counters have a type definition
    #   because these will cause errors in the subsequent parser, which is fine
    #   and in this case, there is no valid generic target to coerce an unspecified counter type to, so it's just going to be a parsing error
    # TODO

    # TODO strip string


    return AI_string


def unreversable_modifications(card):
    # consumes a single internal format, modifies it in place
    # makes changes which are not reversable by AI_to_internal_format
    #   such as stripping and enforcing repeatable capitalization
    # this function will return a dataset which can be directly compared to the dual_processed format for validity
    # since the changes made by this function are not validated by reversion, they should be reviewed by hand
    
    # TODO substitute dashes used to indicate a range
    #   eg 'Roll a d20...\n1–14 | Return all creature cards in your graveyard that were put there from the battlefield this turn to your hand.\n'
    
    # strip text fields
    card['name'] = card['name'].strip()
    if card['main_text'] is not None:
        card['main_text'] = card['main_text'].strip()
    if card['flavor'] is not None:
        card['flavor'] = card['flavor'].strip()

    # coerce some inconsistent rules text to improve parsing consistency for the AI
    if card['main_text'] is not None:
        card['main_text'] = card['main_text'].replace('(Its mana symbols remain unchanged.)', '(Mana symbols on that permanent remain unchanged.)')

    # coerce rarity to specific formatting
    # this creates a robust encoder -> decoder loop target
    card['rarity'] = card['rarity'].capitalize()
    if card['rarity'] == 'Mythic Rare':
        card['rarity'] = 'Mythic'

    # fix alchemy symbol prepended to card names
    card['name'] = re.sub(r'^A-', '', card['name'])

    # convert one-off large nubmers to strings, since numbers are reserved characters
    # normal (smaller) numbers will be converted to unary, but that doesn't make sense for these
    # there also aren't very many number above 20 actually used
    def sub_large_numbers(s):
        s = re.sub(r'100,?000(?![^\{]*\})', 'one-hundred-thousand', s)
        s = re.sub(r'1,?996(?![^\{]*\})', 'nineteen-ninety-six', s)  # date instead of amount?
        s = re.sub(r'1,?000(?![^\{]*\})', 'one-thousand', s)
        s = re.sub(r'200(?![^\{]*\})', 'two-hundred', s)
        s = re.sub(r'100(?![^\{]*\})', 'one-hundred', s)
        s = re.sub(r'50(?![^\{]*\})', 'fifty', s)
        s = re.sub(r'40(?![^\{]*\})', 'forty', s)
        s = re.sub(r'30(?![^\{]*\})', 'thirty', s)
        s = re.sub(r'25(?![^\{]*\})', 'twenty-five', s)
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
        s = s.replace('—',      '-')    # long dash
        s = s.replace('−',      '-')    # minus sign, yes this is a different character from above
        # s = s.replace('•':      '*')  # bullet
        s = s.replace('\u2019', '"')    # single quote
        s = s.replace('\u2018', '"')    # another single quote
        s = s.replace('\xe6',   'ae')   # ae symbol
        s = s.replace('á',      'a')    # a with accent
        s = s.replace('à',      'a')    # a with accent going the other way
        s = s.replace('â',      'a')    # a with caret
        s = s.replace('é',      'e')    # e with accent
        s = s.replace('í',      'i')    # i with accent
        s = s.replace('ñ',      'u')    # n with tilda
        s = s.replace('ö',      'o')    # o with umlaut
        s = s.replace('û',      'u')    # u with caret
        s = s.replace('ú',      'u')    # u with accent
        s = s.replace('ü',      'u')    # u with umlaut
        s = s.replace('π',      'pi')   # pi
        s = s.replace('®',      'r')    # Registered trademark as r
        # s = s.replace('½',      '1/2')  # 1/2
        # s = s.replace('∞',      'inf')  # infinity
        s = s.replace('\u2610', 'na')   # ballot box as na
        return s

    card['name'] = sub_unicode(card['name'])
    card['type'] = sub_unicode(card['type'])
    if card['main_text'] is not None:
        card['main_text'] = sub_unicode(card['main_text'])
    if card['flavor'] is not None:
        card['flavor'] = sub_unicode(card['flavor'])

    if card['main_text'] is not None:
        # remove ability words, which thematically groups cards with a common functionality, but have no actual rules meaning
        card['main_text'] = re.sub(rf'((?<=\s)|(?<=^))({"|".join(MTG_ABILITY_WORDS)})(\s*\-\s*|\s+)', '', card['main_text'])

        card['main_text'] = XYZ_variable_capitalize(card['main_text'])

        # coerce pipes used in card descriptions to colons
        # pipes were only used for one set, and they were used as colons would be. No other cards have pipes in their text.
        # this reduces vocab and improves consistency for the AI
        card['main_text'] = re.sub(r' *\|', ':', card['main_text'])

        # coerce counters to all lower case, to decrease recognition complexity for the AI
        # there are only two cards in the verse (at time of writing) which have capitalized counter names
        #   One card uses 'Shield counter' at the beginning of a sentence
        #   The other card uses the 'CLANK!' counter
        card['main_text'] = re.sub(rf'(?:{"|".join(MTG_COUNTERS)}) counter', lambda x: x.group(0).lower(), card['main_text'])

        # transform small (<= 20) text encoded numbers into decimal
        #   decimal numbers will be encoded to unary during internal_format_to_AI_format, which is more consistent and extensible for the AI
        #   doing the decimal conversion step here instead of in that function provides a consistent encoder -> decoder loop target
        # eg "choose one " -> "choose 1 "
        # remove the card name temporarily, as a precaution against modifying that
        #   Don't need to worry about modifying any reserved words, since none contain delimited number words
        card['main_text'] = card['main_text'].replace(card['name'], '@')
        num_regex = "|".join(nwc.NUMBER_WORDS)
        regex = fr'(?:(?<=^)|(?<=\W))((?:{num_regex})(?:[ \-](?:{num_regex}|and))*(?:[ \-](?:{num_regex}))?)(?=$|\W)'
        def convert(s):
            s = s.group(1)
            ns = nwc.str_to_int(s)
            if int(ns) <= 20:
                return ns
            else:
                return s  # don't convert large nubmers back to decimal (See above step which converts them to words)
        card['main_text'] = re.sub(regex, convert, card['main_text'])
        card['main_text'] = card['main_text'].replace('@', card['name'])  # replace card name

        # remove reminder text (eg keyword explanations)
        card['main_text'] = re.sub(REMINDER_REGEX, '', card['main_text'], flags=re.IGNORECASE)

        # remove trailing whitespace on a line, and remove blank lines, which might for instance by introduced by the above
        # don't remove leading whitespace, which might be intentional formatting
        card['main_text'] = re.sub(r'\s+(?=\n|$)', '', card['main_text'])

        # make field None if it is now empty
        card['main_text'] = card['main_text'] or None

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


def verify_decoder_reverses_encoder(cards, cards_dual_processed):
    # this helps validate that both the encoder and decorder are working properly, or at least have symmetric bugs
    # consumes two lists of internally formatted cards, and compares them
    # if the two are not equal, raises error
    # this is only executed during encode_json_to_AI
    #   and is a test of the program design over the space of the cards from AllPrintings.json
    #   this does not process any AI generated data

    if cards == cards_dual_processed:
        print('Encoder -> Decoder loop passed verification!')
    else:
        for i_card, card in enumerate(cards):
            card_dp = cards_dual_processed[i_card]
            if card != card_dp:
                print('Encoder -> Decoder loop Failed, printing one card diff for context.')
                print(card['name'])
                card_lines    = pprint.pformat(card).split('\n')
                card_dp_lines = pprint.pformat(card_dp).split('\n')
                diff = difflib.unified_diff(card_lines, card_dp_lines)
                diff = list(diff)
                pprint.pprint(diff)
                sys.exit(1)


def encode_json_to_AI_main(json_path, out_path):
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

    # drop the flavor text, we don't encode it in this function
    #   and we need the field omitted for the encoder -> decoder loop verification
    # do this before deduplication so that this field is not considered
    for card in cards:
        del card['flavor']
        if 'b_side' in card: del card['b_side']['flavor']
        if 'c_side' in card: del card['c_side']['flavor']
        if 'd_side' in card: del card['d_side']['flavor']
        if 'e_side' in card: del card['e_side']['flavor']

    # deduplicate the cards
    # We do this after standardization due to some unfortunate artifacts in the json fields, which are addressed in that step
    cards = deduplicate_cards(cards)

    # limit dataset to those cards upon which the AI should train
    cards = limit_to_AI_training_cards(cards)

    # transcribe to AI format, and save in designated location
    cards_AI = [internal_format_to_AI_format(card) for card in cards]
    f = open(out_path, 'w')
    f.write('\n'.join(cards_AI))
    f.close()

    # decode AI format back to internal format, and then compare to the limited dataset from above
    cards_dual_processed = [AI_to_internal_format(card) for card in cards_AI]
    verify_decoder_reverses_encoder(cards, cards_dual_processed)


def encode_json_to_AI_flavor(json_path, out_path):
    pass  # TODO


def encode_json_to_AI_names(json_path, out_path):
    pass  # TODO


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_path", type=str, help="path to names AllPrintings.json")
    parser.add_argument("--out_path", type=str, help="path to output file")
    args = parser.parse_args()

    encode_json_to_AI_main(args.json_path, args.out_path)

