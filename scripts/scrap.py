# contains scraps of code which are partial feature implementations
# largely these were attempts to do something which proved much more difficult than I was prepared to deal with
# and largely these do not work, although a few pieces were intentionally descoped where indicated


# From unreversable_modifications
    # TODO correct when only a part of the card name is used in the main_text to refer to the card
    #   eg "1996 World Champion" may be referred to as "World Champion" in the main text
    #   eg "Crovax, Ascendant Hero" may be referred to as "Crovax" in the main text
    #   apostrophes are also difficult, since sometimes its <name>'s in the possessive, but some card names also contain apostrophes ('Urza's Mine')
    # change these to full name references
    # this is difficult to verify...
    # finally, some cards reference only a part of the name field in the main_text, so we handle that by searching for every possible substring
    # check if the found match in the main_text field is a reference to another name by searching for adjacent capitalized words to form the full name
    # check in the next word in both directions is capitalized
    #   Actually the capitalized check is a bit broken because the substring could be a the beginning/end of a sentence
    #       or 2nd word in a sentence, or a reserved word, or ...
    #   then if the full name from the main text is not equal to the substring, its not a match
    #   repeat in both directions until the string doesn't change
    # Note: this code doesn't really work, and it has a pretty middling runtime
    #   it really needs a much more sophisticated parser to determine whether a partial match should be replaced
    #   or whether the partial match refers to a different object or is part of a bigger different name
    #   and sometimes keywords are in the card name, se we gotta determine how to differentiate usage
    #   Therefore its not enabled...
    # mtgencode's implementation isn't great either
    #   breaking on commas in the name makes some incorrect replacements
    #   eg the card 'Icingdeath, Frost Tyrant' references tokens named 'Icingdeath, Frost Tounge'
    # subs = None
    # for i_substring, substring in enumerate(non_trivial_substrings(name)):
    #     if i_substring == 0:
    #         main_text = main_text.replace(substring, '@')
    #         main_text, subs = temporarily_remove_reserved_words(main_text)
    #     if i_substring > 0:
    #         start = 0
    #         while start is not None:
    #             capture = capture_named_context(substring, main_text, start=start)
    #             if capture is None:
    #                 start = None
    #             else:
    #                 capture, start, end = capture
    #                 if capture == substring:  # check if capture added anything
    #                     q = '\''
    #                     print(f'--Found-- \'{capture + q: <20} #{start: <4} (from {name + ")": <50} -> {repr(main_text)}')
    #                 else:
    #                     print(f'--Dropped-- \'{substring}\' # \'{capture}\'', '->', repr(main_text))
    #                     print('\t->', re.split(r'((?:(?<!\w)\-(?!\w)|[^\w@\-\+\/])+)', main_text))
    #                 start = end  # for next loop iteration
    # main_text = replace_temporarily_removed_reserved_words(main_text, subs)

    # apply strict titlecasing to the card name
    # this gives us a robust target for the AI to internal decoder, since the AI text is all lowercase
    # apply the exact same transformation to the card name when found in the main text
    #   since references to card title are encoded to special characters in the AI format, and we need to be able to find them later
    # Since we chose to let the AI handle capitalization, we've disabled this block. It does otherwise work tho.
    # new_name = titlecase.titlecase(card['name'].lower())  # lower() call ensures titlecaser doesn't try to get too smart about acronym capitalization
    # if card['main_text'] is not None:
    #     segments = re.split(fr"({re.escape(card['name'])})", card['main_text'])
    #     segments = list(segments)
    #     for i_segment, segment in enumerate(segments):
    #         if segment == card['name']:
    #             segments[i_segment] = new_name
    #     card['main_text'] = ''.join(segments)
    # card['name'] = new_name

    # TODO reimplement keyword ordering from mtgencode?
    #   Might improve regularization
    #   but would be a lot of work to get right, since syntax can get fairly complicated, and getting only most part of them wouldn't really help the AI
    #   eg "Equip Shaman, Warlock, or Wizard {1}"
    # text_val = transforms.text_pass_8_equip(text_val)
    # text_val = transforms.text_pass_11_linetrans(text_val)  # standardize order of keywords


# From encode_json_to_AI_main
    # prints out parenthisized text reamining in cards after the reminder text stripping step
    # keep = [
    #     '({T}: Add {G}.)',
    #     '({T}: Add {B}.)',
    #     '({T}: Add {U}.)',
    #     '({T}: Add {R}.)',
    #     '({T}: Add {W}.)',
    #     '({T}: Add {R} or {G}.)',
    #     '({T}: Add {W} or {U}.)',
    #     '({T}: Add {U} or {B}.)',
    #     '({T}: Add {B} or {R}.)',
    #     '({T}: Add {G} or {W}.)',
    #     '({T}: Add {B} or {G}.)',
    #     '({T}: Add {G} or {U}.)',
    #     '({T}: Add {W} or {B}.)',
    #     '({T}: Add {R} or {W}.)',
    #     '({T}: Add {U} or {R}.)',
    #     '({T}: Add {B}, {G}, or {U}.)',
    #     '({T}: Add {B}, {R}, or {G}.)',
    #     '({T}: Add {G}, {U}, or {R}.)',
    #     '({T}: Add {G}, {W}, or {U}.)',
    #     '({T}: Add {R}, {G}, or {W}.)',
    #     '({T}: Add {R}, {W}, or {B}.)',
    #     '({T}: Add {U}, {B}, or {R}.)',
    #     '({T}: Add {U}, {R}, or {W}.)',
    #     '({T}: Add {W}, {B}, or {G}.)',
    #     '({T}: Add {W}, {U}, or {B}.)',
    #     '(Mana symbols on that permanent remain unchanged.)',
    #     '(Do this before you draw.)',
    #     '(Then put Timetwister into its owner\'s graveyard.)',
    #     '(Your party consists of up to 1 each of Cleric, Rogue, Warrior, and Wizard.)',
    #     '(Seat of the Synod isn\'t a spell.)',
    #     '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after I.)',
    #     '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after II.)',
    #     '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after III.)',
    #     '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after IV.)',
    #     '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after V.)',
    #     '(As this Saga enters and after your draw step, add a lore counter.)',
    #     '(Mana abilities can\'t be targeted.)',
    #     '(Piles can be empty.)',
    #     '(Gain the next level as a sorcery to add its ability.)',
    #     '(An ongoing scheme remains face up until it\'s abandoned.)',
    #     '(Start the game with this conspiracy face up in the command zone.)',
    #     '(You may cast a legendary sorcery only if you control a legendary creature or planeswalker.)',
    #     '(Auras with nothing to enchant remain in your graveyard.)',
    #     '(This spell works on creatures that can\'t be blocked.)',
    #     '(The votes can be for different choices or for the same choice.)',
    #     '(It\'s put into its owner\'s junkyard.)',
    #     '(This effect lasts indefinitely.)',
    #     '(Return it only if it\'s on the battlefield.)',
    #     '(Then planeswalk away from this phenomenon.)',
    #     '(This cost is paid as attackers are declared.)',
    #     '(Control of the Equipment doesn\'t change.)',
    #     '(The copy becomes a token.)',
    #     '(It must survive the damage to get the counter.)',
    #     '(This ability triggers after the clash ends.)',
    # ]
    # import tabulate
    # with_context = defaultdict(int)
    # without_context = defaultdict(int)
    # found_parenthesized = defaultdict(int)
    # for card in cards:
    #     if card['main_text'] is not None:
    #         s = re.findall(r'(?:(?<=\n)|(?<=^))([^\(\n]*)(\([^\)]*\))', card['main_text'])
    #         s2 = re.findall(r'\([^\)]*\)', card['main_text'])
    #         for preface, parenthesized in s:
    #             if parenthesized not in keep:
    #                 with_context[preface + parenthesized] += 1
    #                 found_parenthesized[parenthesized] += 1
    #         for parenthesized in s2:
    #             if parenthesized not in found_parenthesized and parenthesized not in keep:
    #                 without_context[parenthesized] += 1
    # with_context = [[v, k] for k,v in with_context.items()]
    # with_context.sort(key = lambda x: [-x[0], x[1]])
    # print(tabulate.tabulate(with_context, tablefmt='pipe'))
    # without_context = [[v, k] for k,v in without_context.items()]
    # without_context.sort(key = lambda x: [-x[0], x[1]])
    # print(tabulate.tabulate(without_context, tablefmt='pipe'))
    # found_parenthesized = [[v, k] for k,v in found_parenthesized.items()]
    # found_parenthesized.sort(key = lambda x: [-x[0], x[1]])
    # print(tabulate.tabulate(found_parenthesized, tablefmt='pipe'))



# these functions execute, but didn't really accomplish what I needed

def in_reserved_word(s):
    # returns boolean indicating whether s is or is a subset of any reserved keyword
    # be careful that some simple words like 'the' appear in keywords

    s = s.lower()

    for reserved in MTG_KEYWORDS + MTG_TYPE_WORDS:
        if s in reserved:
            return True
    return False


def ends_reserved_word(s):
    # returns boolean indicating whether and reserved keywords ends in s
    s = s.lower()
    for reserved in MTG_KEYWORDS + MTG_TYPE_WORDS:
        if reserved.endswith(s):
            return True
    return False


def begins_reserved_word(s):
    # returns boolean indicating whether and reserved keywords begin in s
    s = s.lower()
    for reserved in MTG_KEYWORDS + MTG_TYPE_WORDS:
        if reserved.startswith(s):
            return True
    return False


def all_contiguous_subsets(x, even_boundary_conditions=False):
    # generates all contiguous subsets of an iterable x
    #   largest substrings are yielded first
    #   even_boundary_conditions => only yields subsets with even indexed boundries
    # eg ['a', 'b', 'c'] -> [['a', 'b', 'c'], ['a', 'b'], ['b', 'c'], ['a'], ['b'], ['c']]
    # or with even_boundary_conditions ['a', 'b', 'c', 'd'] -> [['a', 'b', 'c'], ['a'], ['c']]

    # collect all start + end pairs, and then sort by longest ranges
    # this extra sort step gives us longest subsets first
    indeces = []
    for start in range(len(x)):
        if even_boundary_conditions and start%2:
            continue
        for end in reversed(range(start, len(x))):
            if even_boundary_conditions and end%2:
                continue
            indeces.append([start, end])

    # sort by longest subsets first, then secondarily by earliest subset
    indeces.sort(key = lambda x: [x[1] - x[0], -x[0], -x[1]], reverse=True)

    for start, end in indeces:
        yield x[start: end + 1]


def is_small_word(s):
    return titlecase.SMALL_WORDS.search(s) is not None


def non_trivial_substrings(s):
    # returns list of all meaningful substrings of string s
    # each contiguous substring, broken only at word boundaries, is in the return list, as long as
    #   the subset contains atleast one non-small word
    #   first and last token are not small words
    #   the subset is not itself a subset of a reserved word in MTG
    #   is not numerical

    tokens = re.split(r'((?:(?<!\w)\-(?!\w)|[^\w@\-\+\/])+)', s)  # even tokens are words

    would_never_be_a_name_reference = ['You']

    for subset in all_contiguous_subsets(tokens, even_boundary_conditions=True):
        all_words_are_small = all([is_small_word(x) for i, x in enumerate(subset) if not i%2])  # even indeces are words, odd will be word separator characters
        sub_name = ''.join(subset)
        if (not all_words_are_small
            and not is_small_word(subset[0])
            and not is_small_word(subset[-1])
            and sub_name != ''
            and sub_name not in would_never_be_a_name_reference
            and not re.search(r'^[\-\+]?\d+$', sub_name)
            ):
            yield sub_name


def capture_named_context(name, text, start=0):
    # returns the first substring from text containing name, plus possibly some surrounding word(s) whenever
    #   surrounding words are capitalized
    #   includes uncapitalized small words, only when followed/preceeded eventually by a capitalized unreserved word
    #   but will not cross sentence boundaries
    # optionally starts looking at index start in text
    # returns None if there is no match for name in text beginning from start

    pretext = text[:start]
    text = text[start:]

    # break on word boundaries. '-' characters are tricky, let them be in words
    #   but otherwise treate them as non word characters when they exist outside or at the boundary of words
    name_tokens = re.split(r'((?:(?<!\w)\-(?!\w)|[^\w@\-\+\/])+)', name)  # even tokens are words
    text_tokens = re.split(r'((?:(?<!\w)\-(?!\w)|[^\w@\-\+\/])+)', text)  # even tokens are words

    # find start and end of name in text, counted in tokens
    def find_start(a, b):
        for i_token, token in enumerate(b):
            if token == a[0]:
                if all([(i_token + offset < len(b) and token2 == b[i_token + offset]) for offset, token2 in enumerate(a)]):
                    return i_token
        return None

    start = find_start(name_tokens, text_tokens)
    if start is None:
        return None
    end = start + len(name_tokens)

    def include_token(t, prev_token=None, direction='right'):
        if t == '':
            return False

        # check if capitalized
        if t[0] != t[0].upper():
            return False

        # check for capitalized words which are obviously not part of the name
        obviously_not_part_of_the_name = ['When', 'Whenever']
        # common_words_wont_be_used_as_name_reference = ['Black', 'Blue', 'White', 'Green', 'Red']
        if t in obviously_not_part_of_the_name:
            return False

        return True

    # add tokens to the right
    for i_token in range(end, len(text_tokens)):
        is_word = not i_token%2
        token = text_tokens[i_token]

        # mostly we don't process non-words.
        # But do look for boundaries we don't want to cross, such as end of sentences
        #   note that ',+()&' are intentionally not considered boundaries here, since names often contain these
        if not is_word:
            b = False
            for x in '[]{}:;?/\\-!•@\n—':
                if x in token:
                    b = True
                    break
            if b:
                break

            if token in [' - ']:
                break
            continue

        if is_small_word(token):
            continue
        elif include_token(token):
            end = i_token + 1
        else:
            break
    
    # add tokens to the left
    for i_token in range(start-1, -1, -1):
        is_word = not i_token%2
        token = text_tokens[i_token]

        # mostly we don't process non-words.
        # But do look for boundaries we don't want to cross, such as end of sentences
        #   note that ',+()&' are intentionally not considered boundaries here, since names often contain these
        if not is_word:
            b = False
            for x in '[]{}:;?/\\-!•@\n—':
                if x in token:
                    b = True
                    break
            if b:
                break

            if token in [' - ']:
                break
            continue

        prev_token = None
        if i_token > 0:
            prev_token = text_tokens[i_token - 1]
        if is_small_word(token):
            continue
        elif include_token(token, prev_token=prev_token, direction='left'):
            start = i_token
        else:
            break

    # calculate start / end as indeces into the text string
    start_str_index = len(pretext) + sum([len(text_tokens[i_token]) for i_token in range(0, start)])
    end_str_index = len(pretext) + start_str_index + sum([len(text_tokens[i_token]) for i_token in range(start, end)])

    return ''.join(text_tokens[start: end]), start_str_index, end_str_index


def temporarily_remove_reserved_words(s):
    # returns s where all keywords in s have been substituted with a unique reserved character
    # also returns list of substitutions, which will be needed as an arg to the reverse function
    regex = rf'(?:(?<=[\W])|(?<=^))({"|".join(MTG_KEYWORDS + MTG_TYPE_WORDS)})(?=\W|$)'
    reserved_char = '\u2014'  # we know this won't exist in the text when this function is used
    subs = re.findall(regex, s)
    return re.sub(regex, reserved_char, s), subs


def replace_temporarily_removed_reserved_words(s, subs):
    # returns s where all keywords have been replaced
    # reverse of temporarily_remove_reserved_words
    reserved_char = '\u2014'
    for sub in subs:
        s = s.replace(reserved_char, sub, 1)
    return s