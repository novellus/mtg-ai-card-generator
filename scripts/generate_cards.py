import argparse
import datetime
import functools
import os
import pprint
import random
import re
import subprocess
import yaml

from collections import defaultdict

# local imports
import encode
import render
import interface_lstm as lstm
import interface_llm as llm
from mtg_constants import BASIC_LAND_TYPES


FIELD_ORDER = ['name', 'type', 'cost', 'power_toughness', 'loyalty', 'defense', 'main_text', 'author', 'card_number', 'side',
               'flavor', 'nns_names', 'rarity', 'repo_hash', 'repo_link', 'seed', 'seed_diff', 'set_number', 'timestamp', 'unparsed_name',
               'a_side', 'b_side', 'c_side', 'd_side', 'e_side']


def resolve_folder_to_checkpoint_path(path, ext='t7'):
    # return immediately if its a file
    if os.path.isfile(path):
        return path
    assert os.path.isdir(path)

    # search directory for latest checkpoint (measured in epochs trained (eg nubmer in file name))
    #   not recursive
    #   Consider parsing json file and using lowest validtion or training losses instead?
    latest_epoch = -1
    latest_checkpoint = None
    for root, dirs, files in os.walk(path):
        for f_name in files:
            s = re.search(rf'checkpoint_([\d\.]+)\.{ext}', f_name)
            if s is not None:
                epoch = float(s.group(1))
                if epoch > latest_epoch:
                    latest_epoch = epoch
                    latest_checkpoint = os.path.join(root, f_name)

    assert latest_checkpoint is not None
    return latest_checkpoint


def compute_stats(cards, outdir):
    # organize cards into bins, which will be used to compute stats
    # each card may be present in more than one bin

    costless = []  # this list is probably largely invalid cards...
    colorless = []
    colorless_artifacts = []
    mono_colored = defaultdict(list)  # {color: []}
    multicolored = defaultdict(list)  # {'colorA, colorB': []}, including 'three_or_more' as a key
    multisided = defaultdict(list)  # {num_sides: []}
    mana_value = defaultdict(list)  # {value: []}  # AKA converted mana cost
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
        'colorless'                : sorted([card_id(card) for card in colorless]),
        'colorless_artifacts'      : sorted([card_id(card) for card in colorless_artifacts]),
        'costless'                 : sorted([card_id(card) for card in costless]),
        'mono_main_types'          : {k: [card_id(card) for card in v] for k,v in mono_main_types.items()},
        'multi_main_types'         : {k: [card_id(card) for card in v] for k,v in multi_main_types.items()},
        'mana_value'               : {k: [card_id(card) for card in v] for k,v in mana_value.items()},
        'mono_colored'             : {k: [card_id(card) for card in v] for k,v in mono_colored.items()},
        'multicolored'             : {k: [card_id(card) for card in v] for k,v in multicolored.items()},
        'multisided'               : {k: [card_id(card) for card in v] for k,v in multisided.items()},
    }

    f = open(os.path.join(outdir, 'stats.yaml'), 'w')
    f.write(yaml.dump(stats))
    f.close()


def main(args):
    # various AIs are processed one at a time through all cards, 
    #   to prevent multiple AIs from being loaded in vram at the same time
    #   since several AIs have very high load times (several minutes), and persist in memory until terminated

    # handle resuming after interuption
    if args.resume_folder is not None:
        assert os.path.exists(args.resume_folder)
        head, tail = os.path.split(args.resume_folder)
        if tail == '':  # handle path ending in '/'
            head, tail = os.path.split(head)

        s = re.search(r'^(\d+)_(\d+)$', tail)
        assert s is not None, (head, tail)
        base_count = int(s.group(1))
        args.seed = int(s.group(2))
        args.outdir = args.resume_folder

        if args.verbosity > 1:
            print(f'resuming into {args.resume_folder}')

    # handle finishing a yaml file
    if args.finish_yaml is not None:
        assert os.path.exists(args.finish_yaml)
        args.outdir, _ = os.path.split(args.finish_yaml)

        if args.verbosity > 1:
            print(f'finishing {args.finish_yaml}')

    # assign seed
    if args.seed < 0 and not (args.resume_folder or args.finish_yaml):
        args.seed = random.randint(0, 1000000000)
        if args.verbosity > 1:
            print(f'setting seed to {args.seed}')

    # resolve folders to checkpoints, for LSTM networks
    if not args.finish_yaml:
        if args.names_nn is not None:
            args.names_nn = resolve_folder_to_checkpoint_path(args.names_nn)
        if args.main_text_nn is not None:
            args.main_text_nn = resolve_folder_to_checkpoint_path(args.main_text_nn)

    # create / query info text components
    timestamp = datetime.datetime.utcnow().isoformat(sep=' ', timespec='seconds')

    repo_link = None
    try:
        p = subprocess.run('git remote show origin', shell=True, capture_output=True, check=True, cwd=os.getcwd())
        sampled_text = p.stdout.decode('utf-8')
        repo_link = re.search('Fetch URL: ([^\n]+)\n', sampled_text).group(1)
    except:
        repo_link = 'https://github.com/novellus/mtg-ai-card-generator'

    repo_hash = None
    try:
        p = subprocess.run('git rev-parse HEAD', shell=True, capture_output=True, check=True, cwd=os.getcwd())
        repo_hash = p.stdout.decode('utf-8').strip()
    except:
        repo_hash = None

    if not args.finish_yaml:
        nns_names = []
        for nn_path in [args.names_nn, args.main_text_nn]:
            if nn_path is not None:
                head, tail_1 = os.path.split(nn_path)
                _, tail_2 = os.path.split(head)
                tail = os.path.join(tail_2, tail_1)
                name = re.sub(r'checkpoint_|[0\.]+t7', '', tail)
                nns_names.append(name)
        if args.flavor_nn is not None:
            nns_names.append(args.flavor_nn)

    # resolve and create outdir
    if not (args.resume_folder or args.finish_yaml):
        base_count = len(os.listdir(args.outdir))
        args.outdir = os.path.join(args.outdir, f'{base_count:05}_{args.seed}')
        os.makedirs(args.outdir)

    # create cache dirs
    if not args.finish_yaml:
        os.makedirs(os.path.join(args.outdir, 'main_text_cache'), exist_ok=True)
    os.makedirs(os.path.join(args.outdir, 'flavor_cache'), exist_ok=True)

    if args.verbosity > 1:
        print(f'operating in {args.outdir}')

    # generate names, or load cached names file
    # if the requested num_cards is greater than the cached number, regenerate names to the new specifide length
    if not args.finish_yaml:
        cache_path = os.path.join(args.outdir, 'main_text_cache', 'names.yaml')
        sample_new_names = True

        if os.path.exists(cache_path):
            if args.verbosity > 2:
                print(f'Using cached names at {cache_path}')

            f = open(cache_path)
            cards = yaml.load(f.read(), Loader=yaml.FullLoader)
            f.close()

            # trim or exapand the number of names to fit the current num_cards spec
            num_names = args.num_cards
            if args.basic_lands == 'all':
                num_names = args.num_cards * len(BASIC_LAND_TYPES)
            elif type(args.basic_lands) == dict:
                num_names = sum([v for k, v in args.basic_lands.items()])

            if num_names < len(cards):
                cards = cards[:num_names]
                sample_new_names = False

            elif num_names > len(cards):
                if args.verbosity > 2:
                    print(f'Not enough names cached, generating new ones')
                sample_new_names = True

            else:
                sample_new_names = False

        # sample names AI, as a batch
        if sample_new_names:
            if args.verbosity > 2:
                print(f'Sampling names')

            # don't sample names AI if basic_lands are requested
            if args.basic_lands:
                if args.basic_lands == 'all':
                    cards = [{'name': land_type} for land_type in BASIC_LAND_TYPES for _ in range(args.num_cards)]

                elif type(args.basic_lands) == dict:
                    cards = [{'name': type_str} for type_str, num_type in args.basic_lands.items() for _ in range(num_type)]

                else:
                    cards = [{'name': args.basic_lands} for _ in range(args.num_cards)]

            else:
                cards = lstm.sample(nn_path = args.names_nn,
                                    seed = args.seed,
                                    approx_length_per_chunk = lstm.LEN_PER_NAME,
                                    num_chunks = args.num_cards,
                                    parser = functools.partial(encode.AI_to_internal_format, spec='names'),
                                    verbosity = args.verbosity,
                                    gpu = args.lstm_gpu)

            if args.verbosity > 2:
                print(f'Caching names to {cache_path}')

            f = open(cache_path, 'w')
            f.write(yaml.dump(cards))
            f.close()
        # Note that each card in cards will only contain the 'name' field at this point

    # sample main text
    if not args.finish_yaml:
        # increment seed each card and side for improved uniqueness
        # txt2img uses the seed to directly determine the base noise from which the image is generated
        #   meaning identical seeds produce visually similar images, even given different prompts
        # the LSTM samplers are also a bit biased by the seed, despite being whispered unique names
        seed_diff = 0

        for i_card, card in enumerate(cards):
            sanitized_name = re.sub('/', '', card['name'])
            cache_path = os.path.join(args.outdir, 'main_text_cache', f"{i_card:05} {sanitized_name}.yaml")

            # use cached text file, if any
            if os.path.exists(cache_path):
                if args.verbosity > 2:
                    print(f'Using cached main_text {i_card + 1} / {len(cards)}, at {cache_path}')
                
                f = open(cache_path)
                card = yaml.load(f.read(), Loader=yaml.FullLoader)
                f.close()

                # replace 'a_side' backlinks, which are omitted from save file
                if 'b_side' in card: card['b_side']['a_side'] = card
                if 'c_side' in card: card['c_side']['a_side'] = card
                if 'd_side' in card: card['d_side']['a_side'] = card
                if 'e_side' in card: card['e_side']['a_side'] = card

                cards[i_card] = card

                # increment seed_diff for every side, to keep parity when cached files do / don't exist
                seed_diff += 1
                if 'b_side' in card: seed_diff += 1
                if 'c_side' in card: seed_diff += 1
                if 'd_side' in card: seed_diff += 1
                if 'e_side' in card: seed_diff += 1

            else:
                # sample main_text AI
                #   which may generate several card sides
                if args.verbosity > 0:
                    print(f'Sampling main_text {i_card + 1} / {len(cards)}')

                if args.basic_lands:
                    assert card['name'] in BASIC_LAND_TYPES, f'Specified a basic land type that is not defined in mtg_constants.py: "{card["name"]}", this is not allowed. Go define it?'
                    card.update({'cost'            : None,
                                 'type'            : BASIC_LAND_TYPES[card['name']].type,
                                 'loyalty'         : None,
                                 'power_toughness' : None,
                                 'defense'         : None,
                                 'rarity'          : 'Basic Land',
                                 'main_text'       : BASIC_LAND_TYPES[card['name']].main_text,
                                 'side'            : 'a',
                                })

                else:
                    card.update(lstm.sample(nn_path = args.main_text_nn,
                                            seed = args.seed + seed_diff,
                                            approx_length_per_chunk = lstm.LEN_PER_MAIN_TEXT,
                                            num_chunks = 1,
                                            parser = functools.partial(encode.AI_to_internal_format, spec='main_text'),
                                            whisper_text = f"{card['unparsed_name']}①",
                                            whisper_every_newline = 1,
                                            verbosity = args.verbosity,
                                            gpu = args.lstm_gpu)
                    )

                def finish_side(side):
                    nonlocal seed_diff

                    # add card + generator info text as properties of the card
                    # this enables repeatable rendering from the saved card data
                    side['set_number'] = base_count
                    side['seed'] = args.seed
                    side['seed_diff'] = seed_diff
                    side['card_number'] = i_card

                    side['timestamp'] = timestamp
                    side['nns_names'] = nns_names
                    side['author'] = args.author
                    side['repo_link'] = repo_link
                    side['repo_hash'] = repo_hash

                    # increment seed_diff for every side
                    seed_diff += 1

                finish_side(card)
                if 'b_side' in card: finish_side(card['b_side'])
                if 'c_side' in card: finish_side(card['c_side'])
                if 'd_side' in card: finish_side(card['d_side'])
                if 'e_side' in card: finish_side(card['e_side'])

                # Cache generated card
                # remove 'a_side' back references (see below)
                if args.verbosity > 2:
                    print(f'Caching main text to {cache_path}')

                f = open(cache_path, 'w')
                f.write(yaml.dump(encode.limit_fields(card, blacklist=['a_side'])))
                f.close()

    # load the yaml card data
    if args.finish_yaml:
        f = open(args.finish_yaml)
        cards = yaml.load(f.read(), Loader=yaml.FullLoader)
        f.close()

        # replace 'a_side' backlinks, which are omitted from save file
        for i_card, card in enumerate(cards):
            if 'b_side' in card: card['b_side']['a_side'] = card
            if 'c_side' in card: card['c_side']['a_side'] = card
            if 'd_side' in card: card['d_side']['a_side'] = card
            if 'e_side' in card: card['e_side']['a_side'] = card

    # sample flavor text
    if args.no_flavor:
        if args.verbosity > 2:
            print(f'Skipping flavor')

        for i_card, card in enumerate(cards):
            card['flavor'] = ''
            if 'b_side' in card: card['b_side']['flavor'] = ''
            if 'c_side' in card: card['c_side']['flavor'] = ''
            if 'd_side' in card: card['d_side']['flavor'] = ''
            if 'e_side' in card: card['e_side']['flavor'] = ''

    else:
        for i_card, card in enumerate(cards):
            sanitized_name = re.sub('/', '', card['name'])
            cache_path = os.path.join(args.outdir, 'flavor_cache', f"{i_card:05} {sanitized_name}.yaml")

            # use cached text file, if any
            if os.path.exists(cache_path):
                if args.verbosity > 2:
                    print(f'Using cached text {i_card + 1} / {len(cards)}, at {cache_path}')
                
                f = open(cache_path)
                cached_flavor = yaml.load(f.read(), Loader=yaml.FullLoader)
                f.close()

                card['flavor'] = cached_flavor['flavor']
                if 'b_side' in cached_flavor: card['b_side']['flavor'] = cached_flavor['b_side']['flavor']
                if 'c_side' in cached_flavor: card['c_side']['flavor'] = cached_flavor['c_side']['flavor']
                if 'd_side' in cached_flavor: card['d_side']['flavor'] = cached_flavor['d_side']['flavor']
                if 'e_side' in cached_flavor: card['e_side']['flavor'] = cached_flavor['e_side']['flavor']

            elif 'flavor' not in card or card['flavor'] == '':  # allow flavor to be defined when finishing a yaml
                # sample flavor AI for each card side
                if args.verbosity > 0:
                    print(f'Sampling flavor {i_card + 1} / {len(cards)} (slow)')

                def finish_side(side):
                    if args.verbosity > 2 and 'a_side' in side:
                        print(f'Sampling flavor for side {side["side"]}')

                    side['flavor'] = llm.sample_flavor(card = card,
                                                       model = args.flavor_nn,
                                                       gpu_memory = args.gpu_memory,
                                                       cpu_memory = args.cpu_memory,
                                                       seed = side['seed'] + side['seed_diff'],
                                                       verbosity = args.verbosity)

                finish_side(card)
                if 'b_side' in card: finish_side(card['b_side'])
                if 'c_side' in card: finish_side(card['c_side'])
                if 'd_side' in card: finish_side(card['d_side'])
                if 'e_side' in card: finish_side(card['e_side'])

                # Extract and cache flavor text
                if args.verbosity > 2:
                    print(f'Caching flavor text to {cache_path}')

                f = open(cache_path, 'w')
                f.write(yaml.dump(encode.limit_fields(card, whitelist=['flavor', 'b_side', 'c_side', 'd_side', 'e_side'])))
                f.close()

    # terminate flavor AI to free up vram for later steps
    llm.terminate_server(args.verbosity)

    # save parsed card data for searchable/parsable reference, search, debugging, etc
    # remove the 'a_side' back references because the yaml dump doesn't handle recursion very well
    #   the recursion is handled, but not at the highest available location, creating redundant data which is difficult to read + hand-modify
    #   in addition I'm a bit worried that the deeper-than-intended recursion level saved in the yaml file will result in an incorrect data structure on reload
    #   and finally, its easy enough to add the backlink back in at reload time.
    # Also order fields for human readability
    yaml_data = [encode.limit_fields(card, blacklist=['a_side']) for card in cards]
    yaml_data = [encode.order_dict_fields(card, FIELD_ORDER) for card in yaml_data]
    f = open(os.path.join(args.outdir, 'card_data.yaml'), 'w')
    f.write(yaml.dump(yaml_data, sort_keys=False))
    f.close()

    # statistics over cards
    if not args.no_stats:
        compute_stats(cards, args.outdir)

    # render the cards
    if args.no_render:
        if args.verbosity > 2:
            print(f'Skipping render')
    else:
        for card in cards:
            use_type = True
            if args.basic_lands:
                use_type = False
            render.render_card(card, args.sd_nn, args.outdir, args.no_art, args.verbosity, hr_upscale=args.hr_upscale, use_type=use_type)

    # terminate stable diffusion AI to free up vram
    render.a1sd.terminate_server(args.verbosity)

    if args.to_pdf:
        import to_pdf
        to_pdf.main(args.outdir, args.verbosity)


if __name__ == '__main__':
    yaml_load = functools.partial(yaml.load, Loader=yaml.FullLoader)  # cache this partial func with args for the arg parser below

    parser = argparse.ArgumentParser()
    parser.add_argument("--names_nn", type=str, help="path to names nn checkpoint, or path to folder with checkpoints (uses longest trained)")
    parser.add_argument("--main_text_nn", type=str, help="path to main_text nn checkpoint, or path to folder with checkpoints (uses longest trained)")
    parser.add_argument("--flavor_nn", type=str, help="name of flavor llm, in style recognized by text-generation-webui (eg \"timdettmers_guanaco-65b-merged\")")
    parser.add_argument("--sd_nn", default=None, type=str, help="name of stable diffusion model, in style recognized by stable-diffusion-webui (eg \"nov_mtg_art_v2_3.ckpt [76fcbf0ef5]\")")
    parser.add_argument("--gpu-memory", type=int, help="passed to text-generation-webui for llm server memory limits. Does not apply to other nns. See text-generation-webui docs for more info.")
    parser.add_argument("--cpu-memory", type=int, help="passed to text-generation-webui for llm server memory limits. Does not apply to other nns. See text-generation-webui docs for more info.")
    parser.add_argument("--outdir", type=str, help="path to outdir. Files are saved in a subdirectory based on seed")
    parser.add_argument("--num_cards", type=int, help="number of cards to generate", default=10)
    parser.add_argument("--seed", type=int, help="if negative or not specified, a random seed is assigned", default=-1)
    parser.add_argument("--no_art", action='store_true', help="disable txt2img render, which occupies a large portion of the generation time. Useful for debugging/testing.")
    parser.add_argument("--no_flavor", action='store_true', help="disable flavor generation, which occupies most of the generation time. Useful for debugging/testing.")
    parser.add_argument("--no_render", action='store_true', help="disables rendering altogether. Superscedes --no_art. Still generates yaml and other optional output files.")
    parser.add_argument("--hr_upscale", type=int, default=None, help="Upscale art by specified factor. Only applies to non-cached art. Seriously increases the processing time as this factor increases. Art is always rendered at 512x512px before upscaling (if any) and then scaled/cropped to fit the card frame. At a value of 2, art will be upscaled to 1024x1024px before fitting to card.")
    parser.add_argument("--author", type=str, default='Novellus Cato', help="author name, displays on card face")
    parser.add_argument("--no_stats", action='store_true', help="disables stats.yaml output file")
    parser.add_argument("--resume_folder", type=str, help="Path to folder. resumes generating into specified output folder, skips sampling AIs with cached outputs and skips rendering existing card files.")
    parser.add_argument("--finish_yaml", type=str, help="Path to yaml. finishes generating cards from specified yaml. The yaml input file is usually hand constructed or modified. Will not sample new names or main_text. Will sample flavor AI, sample art AI, and render cards depending on other args.")
    parser.add_argument("--basic_lands", type=yaml_load, nargs='?', const='all', default=None, help="Generate basic lands instead of normal cards. Overwrites names and main_text samplers with appropriate hard-coded fields, but still performs flavor and art sampling. Optional type string may be fed to this argument (eg '--basic_lands forest'), and if type is not specified, will generate all types of hard-coded lands num_cards times each. Can also specify a yaml-encoded dict of types to quantity instead, in which case --num_cards is ignored. Types specifed at CLI must exist in mtg_constants.py. Not compatible with --finish_yaml, if you have a yaml you don't need this arg anyway.")
    parser.add_argument("--lstm_gpu", type=int, default=0, help='select gpu device for sampling LSTMs')
    parser.add_argument("--to_pdf", action='store_true', help='automatically execute to_pdf.py on the output folder to create a printable file.')
    parser.add_argument("--verbosity", type=int, default=1)
    args = parser.parse_args()

    assert args.sd_nn or args.no_art, "must specify either the stable diffusion model, or --no_art flag"
    assert not (args.resume_folder and args.finish_yaml), "must specify only one of resume_folder or finish_yaml"

    try:
        main(args)
    except:
        llm.terminate_server(args.verbosity)
        render.a1sd.terminate_server(args.verbosity)
        raise

