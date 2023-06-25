import json
import os
import yaml
import numpy as np
import pprint
import math
import io
import itertools
import requests
import base64
import base58
import re
import sys
import tabulate
import titlecase
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont




# ## parse allPrintings.json
# f = open('../raw_data_sources/AllPrintings.json')
# j = json.load(f)
# f.close()
# data = defaultdict(int)
# for k_set, v_set in list(j['data'].items()):
#     for card in v_set['cards']:
#         if re.search(r'agent of the shadow thieves', card['name'].lower()):
#             del card['foreignData']
#             pprint.pprint(card)
#         # if 'text' in card and re.search(r'd20', card['text'].lower()):
#         #     del card['foreignData']
#         #     pprint.pprint(card)
#         #     sys.exit()
#         # if 'power' in card and re.search(r'²', card['power'].lower()):
#         #     del card['foreignData']
#         #     pprint.pprint(card)
#         #     sys.exit()
#         # if re.search(r'urza', card['type'].lower()):
#         #     del card['foreignData']
#         #     pprint.pprint(card)
#         # if 'manaCost' in card and re.search(r'1000000', card['manaCost'].lower()):
#         #     del card['foreignData']
#         #     pprint.pprint(card)
#         #     sys.exit()
#         # for field in card:
#         #     if type(card[field]) == str and re.search(r'blinkmoth', card[field].lower()):
#         #         # del card['foreignData']
#         #         pprint.pprint(card)
#         #         sys.exit()
#         # for field in ['name']:
#         #     if field in card:
#         #         for c in card[field]:
#         #             data.add(c)
#         # for field in ['text', 'name']:
#         #     if field in card:
#         #         if re.search(r'\|', card[field]):
#         #             del card['foreignData']
#         #             pprint.pprint(card)
#         #             sys.exit()
#         # if 'side' in card and card['side'] in ['e']:
#         #     del card['foreignData']
#         #     pprint.pprint(card)
#         #     sys.exit()
#         # if 'text' in card:
#         #     # s = re.findall(r'[^\n]*(?<!\d|[XYZ])\+(?!\d|[XYZ])[^\n]*', card['text'])
#         #     s = re.findall(r'[^\n]*(?<=\d|[XYZ])\+(?=\d|[XYZ])[^\n]*', card['text'])
#         #     for x in s:
#         #         data[x] += 1
#         # for t in card['types'] + card['subtypes'] + card['supertypes']:
#         #     data.add(t)
#         # if 'text' in card:
#         #     for x in re.findall('(?:(?<=^)|(?<=\n))[^\v—-−]+[—-−]', card['text']):
#         #         data.add(x)
#         # for subset in all_continguous_subsets(card['name'].split()):  # tokenize on whitespace
#         #     sub_name = ' '.join(subset)  # TODO assumed space...
#         #     if sub_name != card['name']:
#         #         if 'text' in card and sub_name.lower() in card['text']:
#         #             print(f'{sub_name: <50} -> {repr(card["text"])}')
#         # if 'text' in card and re.search(r'\|', card['text'].lower()):
#         #     print(card['text'])
#         # data[len(card['name'])] = card['name']
# pprint.pprint(data)




## plot lstm param size
#       # layer size  # num layers  # num params
# a = [(1024,         3,            21296046),
#      (512,          3,            5406638),
#      (256,          3,            1394094),
#      (128,          3,            370862),
#      (64,           3,            105006),
#      (1024,         2,            12903342),
#      (512,          2,            3307438),
#      (256,          2,            868782),
#      (128,          2,            239278),
#      (64,           2,            71982),
#      (1024,         4,            29688750),
#      (512,          4,            7505838),
#      (256,          4,            1919406),
#      (128,          4,            502446),
#      (64,           4,            138030),
#      (1024,         5,            38081454),
#      (1024,         6,            46474158),
#     ]



## test encoding
# import re
# a = {'W': '{W}', 'U': '{U}', 'B': '{B}', 'R': '{R}', 'G': '{G}', 'P': '{P}', 'S': '{S}', 'X': '{X}', 'C': '{C}', 'E': '{E}', 'WP': '{W/P}', 'UP': '{U/P}', 'BP': '{B/P}', 'RP': '{R/P}', 'GP': '{G/P}', '2W': '{2/W}', '2U': '{2/U}', '2B': '{2/B}', '2R': '{2/R}', '2G': '{2/G}', 'WU': '{W/U}', 'WB': '{W/B}', 'RW': '{R/W}', 'GW': '{G/W}', 'UB': '{U/B}', 'UR': '{U/R}', 'GU': '{G/U}', 'BR': '{B/R}', 'BG': '{B/G}', 'RG': '{R/G}', 'PW': '{P/W}', 'PU': '{P/U}', 'PB': '{P/B}', 'PR': '{P/R}', 'PG': '{P/G}', 'W2': '{W/2}', 'U2': '{U/2}', 'B2': '{B/2}', 'R2': '{R/2}', 'G2': '{G/2}', 'UW': '{U/W}', 'BW': '{B/W}', 'WR': '{W/R}', 'WG': '{W/G}', 'BU': '{B/U}', 'RU': '{R/U}', 'UG': '{U/G}', 'RB': '{R/B}', 'GB': '{G/B}', 'GR': '{G/R}'}
# new = set()
# for k, v in a.items():
#     v_inside = v[1:-1]
#     for sym in v_inside.split('/'):
#         new.add(sym)
# print(sorted(list(new)))




# ## test card rendering
# from PIL import Image
# import datetime
# import render
# timestamp = datetime.datetime.utcnow().isoformat(sep=' ', timespec='seconds')
# nns_names = ['names_000/00003380.t7', 'main_text_000/00003380.t7', 'flavor_000/00003380']
# card = {'cost': '{1}{1000000}{R}',
#         'flavor': '"the high when secrets, muse them specious."',
#         'loyalty': None,
#         'defense': None,
#         'main_text': '{W}, 1{T}: Udvise the Betrayer deals damage {T} to target creature \nwithout         flying each opponent\'s choice and put the rest into the battlefield. It gains haste. Sacrifice it at the beginning of the next end step.',
#         'type': 'Creature - Dinosaur',
#         'name': 'Udvise the Betrayer',
#         'power_toughness': '4/1',
#         'rarity': 'uncommon',
#         'set_number' : 0,
#         'seed' : 210755924,
#         'seed_diff' : 3,
#         'card_number' : 14,
#         'timestamp' : timestamp,
#         'nns_names' : nns_names,
#         'author' : 'Novellus Cato',
#         'repo_link' : 'https://github.com/novellus/mtg-ai-card-generator',
#         'repo_hash' : '5325ac6ce2444a19c6c6097f6a589985826d8d5a',
#         'side' : 'a',
#         'b_side': {'cost': '{1}{R}',
#                    'flavor': '"the high when secrets, muse them specious."',
#                    'loyalty': None,
#                    'defense': 4157585,
#                    'main_text': '{W}, {T},: Udvise the Betrayer deals damage {T} to target creature \n    * without flying each opponent\'s choice and put the rest into the battlefield. It gains haste. Sacrifice it at the beginning of the next end step.',
#                    'type': 'Creature - Dinosaur',
#                    'name': 'Udvise the Betrater',
#                    'power_toughness': None,
#                    'rarity': 'uncommon',
#                    'set_number' : 0,
#                    'seed' : 210755924,
#                    'seed_diff' : 3,
#                    'card_number' : 14,
#                    'timestamp' : timestamp,
#                    'nns_names' : nns_names,
#                    'author' : 'Novellus Cato',
#                    'repo_link' : 'https://github.com/novellus/mtg-ai-card-generatorhttps://github.com/novellus/mtg-ai-card-generator',
#                    'repo_hash' : '5325ac6ce2444a19c6c6097f6a589985826d8d5a',
#                    'side' : 'b',
#                   }
#         }
# card['b_side']['a_side'] = card
# render.render_card(card, outdir='.', sd_nn=None, no_art=True, verbosity=2, overwrite=True)






## decode main text
# import generate_cards
# import json
# import pprint
# a=generate_cards.parse_mtg_cards(r'|1incendiary command|5sorcery|4|6|7|8|9[[choose two ~ = @ deals &^^^^ damage to target player or planeswalker. = @ deals &^^ damage to each creature. = destroy target nonbasic land. = each player discards all the cards in their hand, then draws that many cards.]]|3{^^^RRRR}|0A|', 2)
# pprint.pprint(a)




# # check max line lengths
# for f_name in ['main_text.txt', 'flavor.txt', 'names.txt']:
#     path = os.path.join('../encoded_data_sources', f_name)
#     f = open(path)
#     f_con = f.read()
#     f.close()
#     lines = f_con.split('\n')
#     max_len = 0
#     max_line = None
#     for line in lines:
#         if len(line) > max_len:
#             max_len = len(line)
#             max_line = line
#     print(f'{f_name} -> {max_len} "{max_line}"')




# ## pretty print
# a = """{"object":"card","id":"0000579f-7b35-4ed3-b44c-db2a538066fe","oracle_id":"44623693-51d6-49ad-8cd7-140505caf02f","multiverse_ids":[109722],"mtgo_id":25527,"mtgo_foil_id":25528,"tcgplayer_id":14240,"cardmarket_id":13850,"name":"Fury Sliver","lang":"en","released_at":"2006-10-06","uri":"https://api.scryfall.com/cards/0000579f-7b35-4ed3-b44c-db2a538066fe","scryfall_uri":"https://scryfall.com/card/tsp/157/fury-sliver?utm_source=api","layout":"normal","highres_image":true,"image_status":"highres_scan","image_uris":{"small":"https://cards.scryfall.io/small/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979","normal":"https://cards.scryfall.io/normal/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979","large":"https://cards.scryfall.io/large/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979","png":"https://cards.scryfall.io/png/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.png?1562894979","art_crop":"https://cards.scryfall.io/art_crop/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979","border_crop":"https://cards.scryfall.io/border_crop/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979"},"mana_cost":"{5}{R}","cmc":6.0,"type_line":"Creature — Sliver","oracle_text":"All Sliver creatures have double strike.","power":"3","toughness":"3","colors":["R"],"color_identity":["R"],"keywords":[],"legalities":{"standard":"not_legal","future":"not_legal","historic":"not_legal","gladiator":"not_legal","pioneer":"not_legal","explorer":"not_legal","modern":"legal","legacy":"legal","pauper":"not_legal","vintage":"legal","penny":"legal","commander":"legal","brawl":"not_legal","historicbrawl":"not_legal","alchemy":"not_legal","paupercommander":"restricted","duel":"legal","oldschool":"not_legal","premodern":"not_legal"},"games":["paper","mtgo"],"reserved":false,"foil":true,"nonfoil":true,"finishes":["nonfoil","foil"],"oversized":false,"promo":false,"reprint":false,"variation":false,"set_id":"c1d109bc-ffd8-428f-8d7d-3f8d7e648046","set":"tsp","set_name":"Time Spiral","set_type":"expansion","set_uri":"https://api.scryfall.com/sets/c1d109bc-ffd8-428f-8d7d-3f8d7e648046","set_search_uri":"https://api.scryfall.com/cards/search?order=set\u0026q=e%3Atsp\u0026unique=prints","scryfall_set_uri":"https://scryfall.com/sets/tsp?utm_source=api","rulings_uri":"https://api.scryfall.com/cards/0000579f-7b35-4ed3-b44c-db2a538066fe/rulings","prints_search_uri":"https://api.scryfall.com/cards/search?order=released\u0026q=oracleid%3A44623693-51d6-49ad-8cd7-140505caf02f\u0026unique=prints","collector_number":"157","digital":false,"rarity":"uncommon","flavor_text":"\"A rift opened, and our arrows were abruptly stilled. To move was to push the world. But the sliver's claw still twitched, red wounds appeared in Thed's chest, and ribbons of blood hung in the air.\"\n—Adom Capashen, Benalish hero","card_back_id":"0aeebaf5-8c7d-4636-9e82-8c27447861f7","artist":"Paolo Parente","artist_ids":["d48dd097-720d-476a-8722-6a02854ae28b"],"illustration_id":"2fcca987-364c-4738-a75b-099d8a26d614","border_color":"black","frame":"2003","full_art":false,"textless":false,"booster":true,"story_spotlight":false,"edhrec_rank":5708,"penny_rank":10983,"prices":{"usd":"0.38","usd_foil":"4.13","usd_etched":null,"eur":"0.02","eur_foil":"1.49","tix":"0.02"},"related_uris":{"gatherer":"https://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid=109722","tcgplayer_infinite_articles":"https://infinite.tcgplayer.com/search?contentMode=article\u0026game=magic\u0026partner=scryfall\u0026q=Fury+Sliver\u0026utm_campaign=affiliate\u0026utm_medium=api\u0026utm_source=scryfall","tcgplayer_infinite_decks":"https://infinite.tcgplayer.com/search?contentMode=deck\u0026game=magic\u0026partner=scryfall\u0026q=Fury+Sliver\u0026utm_campaign=affiliate\u0026utm_medium=api\u0026utm_source=scryfall","edhrec":"https://edhrec.com/route/?cc=Fury+Sliver"}}"""
# import json
# import pprint
# pprint.pprint(json.loads(a))





# ## list learning rates
# grad_accumulation = True
# r = 0.005
# N = 1 if grad_accumulation else 128
# steps = N * 1000
# reduce_every = 1 if grad_accumulation else 5
# reduce_by = 0.99 if grad_accumulation else 0.95
# init_i = 1
# for i in range(init_i, init_i + steps):
#     if i == init_i: i = 1
#     if i == 1 or not i % (reduce_every * N):
#         print(f'{r:.3}:{i}')
#         r = r * reduce_by




# ## parameterized grid from txt2img
# # upscalers = ['Lanczos', 'ESRGAN_4x', 'LDSR', 'R-ESRGAN 4x+', 'ScuNET GAN']
# # upscalers = ['Lanczos', 'LDSR', 'R-ESRGAN 4x+']
# upscaler = 'LDSR'
# denoises = list(np.linspace(0.1, 0.75, 10))
# names = ['Sandrax, Hand of Clanch', 'Cached Skize', 'Triather\'s Acolyte', 'Hermit Hygon', 'Bag of Multing']
# left_margin = 200
# top_margin = 50
# grid = Image.new(mode='RGBA', size=(left_margin + 1024 * len(denoises), top_margin + 1024 * len(names)), color=(0,0,0,255))
# d = ImageDraw.Draw(grid)
# font = ImageFont.truetype('../image_templates/fonts/beleren-b.ttf', size=24)
# target_size = (1500, 1937)
# upscale = target_size[1] / 1024
# side_crop = math.floor((1024 - target_size[0] / upscale) / 2)
# crop_darkener = Image.new(mode='RGBA', size=(1024, 1024), color=(0,0,0,0))
# dark_edge = Image.new(mode='RGBA', size=(side_crop, 1024), color=(0,0,0,128))
# crop_darkener.alpha_composite(dark_edge, dest=(0, 0))
# crop_darkener.alpha_composite(dark_edge, dest=(1024 - side_crop, 0))
# # for i_name, name in enumerate(names):
# for i_denoise, denoise in enumerate(denoises):
#     d.text((left_margin + 512 + 1024 * i_denoise, top_margin - 10), text=str(denoise), font=font, anchor='md', fill=(255,255,255,255))
#     for i_name, name in enumerate(names):
#         os.makedirs(f'tmp_{name}', exist_ok=True)
#         print(f'Processing {i_name + (i_denoise * len(names)) + 1} / {len(denoises) * len(names)}')
#         if i_denoise == 0:
#             d.text((left_margin - 10, top_margin + 512 + 1024 * i_name), text=name, font=font, anchor='rm', fill=(255,255,255,255))
#         UID = upscaler[:2] + str(denoise)
#         cache = os.path.join(f'tmp_{name}', f'{UID}.png')
#         im = None
#         if os.path.exists(cache):
#             im = Image.open(cache)
#         else:
#             payload = {
#                 'prompt': f'{name}, high fantasy',
#                 'negative_prompt': 'mtgframe5, mtgframe6, mtgframe7, mtgframe8, mtgframe10, mtgframe11, blurry, text',
#                 'steps': 20,
#                 'batch_size': 1,
#                 'n_iter': 1,
#                 'width': 512,
#                 'height': 512,
#                 'sampler_index': 'Euler',  # also available: 'sampler_name'... ?
#                 'seed': 481992436 + i_name,
#                 'enable_hr': True,
#                 'hr_scale': 2,
#                 'hr_upscaler': upscaler,
#                 'denoising_strength': denoise,
#             }
#             response = requests.post('http://127.0.0.1:7860/sdapi/v1/txt2img', json=payload)
#             response = response.json()
#             image_data = response['images'][0]
#             im = Image.open(io.BytesIO(base64.b64decode(image_data)))
#             im.save(cache)
#         pos = (left_margin + 1024 * i_denoise, top_margin + 1024 * i_name)
#         grid.paste(im, box=pos)
#         grid.alpha_composite(crop_darkener, dest=pos)
# grid.save(f'tmp.png')






# ## process PoetryFoundationData.csv
# # write our own csv parser since the built-in csvreader can't handle literal newlines in the encoded strings
# f = open('../raw_data_sources/PoetryFoundationData.csv')
# header = f.readline()
# f_con = f.read()
# f.close()
# headers = {h.strip():i for i,h in enumerate(header.split(','))}
# entries = []
# new_entry = True
# is_inside_quotes = False
# quote_char = None
# for i_char, char in enumerate(f_con):
#     if new_entry:
#         entries.append([''])
#         new_entry = False
#     if char == ',' and not is_inside_quotes:
#         entries[-1].append('')
#         continue
#     if char == '"':
#         if is_inside_quotes and char == quote_char:
#             is_inside_quotes = False
#             continue
#         elif not is_inside_quotes:
#             is_inside_quotes = True
#             quote_char = char
#             continue
#     if char == '\n' and not is_inside_quotes:
#         new_entry = True
#         continue
#     entries[-1][-1] += char
# # convert all consecutive whitespace to a single space, and trim entries
# #   also eliminate characters I don't want in the dataset
# for i_entry, entry in enumerate(entries):
#     for i_val, val in enumerate(entry):
#         val = re.sub('[`~¢£¤´þ˚άέίαΑΒγδεηθιΙκΚλΛμνξοΟρΡςσΣק€↔⊖⎯─▶◀★☽♂♥❖兰宜旦未沙牛目肉艾麵ﬁﬂ�τχΧ]', '', val)
#         val = re.sub('\u200b', '', val)
#         val = re.sub('\u2060', '', val)
#         val = re.sub('\ufeff', '', val)
#         val = re.sub('\u2014', '', val)
#         val = re.sub('\xad', '', val)
#         val = val.replace('∓', '+-')
#         val = val.replace('•', '')
#         val = val.replace('⊖', '-')
#         val = re.sub('¼', '1/4', val)
#         val = re.sub('½', '1/2', val)
#         val = re.sub('̶', '', val)
#         val = re.sub('˝', '"', val)
#         val = re.sub('Ä', 'A', val)
#         val = re.sub('↵', '', val)
#         val = re.sub('²', '', val)
#         val = re.sub('„', '"', val)
#         val = re.sub('―', '-', val)
#         val = re.sub(r'́', '', val)
#         val = re.sub(r'̧', '', val)
#         val = re.sub(r'̄', '', val)
#         val = re.sub(r'̈', '', val)
#         val = re.sub(r'̃', '', val)
#         val = re.sub('∓', '+-', val)
#         val = re.sub('⊖', '-', val)
#         val = re.sub('·', '', val)
#         val = re.sub('¿', '?', val)
#         val = re.sub('×', 'x', val)
#         val = re.sub('ß', 'B', val)
#         val = re.sub('À', 'A', val)
#         val = re.sub('Á', 'A', val)
#         val = re.sub('å', 'a', val)
#         val = re.sub('ç', 'c', val)
#         val = re.sub('Ç', 'C', val)
#         val = re.sub('È', 'E', val)
#         val = re.sub('É', 'E', val)
#         val = re.sub('ë', 'e', val)
#         val = re.sub('Ë', 'E', val)
#         val = re.sub('ì', 'i', val)
#         val = re.sub('Í', 'I', val)
#         val = re.sub('î', 'I', val)
#         val = re.sub('Î', 'I', val)
#         val = re.sub('ï', 'i', val)
#         val = re.sub('ð', 'o', val)
#         val = re.sub('ò', 'o', val)
#         val = re.sub('ó', 'o', val)
#         val = re.sub('Ó', 'O', val)
#         val = re.sub('ô', 'o', val)
#         val = re.sub('Ô', 'O', val)
#         val = re.sub('Ö', 'O', val)
#         val = re.sub('Ø', '0', val)
#         val = re.sub('ø', '0', val)
#         val = re.sub('ù', 'u', val)
#         val = re.sub('Ú', 'U', val)
#         val = re.sub('ý', 'y', val)
#         val = re.sub('ÿ', 'y', val)
#         val = re.sub('ā', 'a', val)
#         val = re.sub('č', 'c', val)
#         val = re.sub('đ', 'd', val)
#         val = re.sub('Đ', 'D', val)
#         val = re.sub('ē', 'e', val)
#         val = re.sub('ĕ', 'e', val)
#         val = re.sub('ę', 'e', val)
#         val = re.sub('ě', 'e', val)
#         val = re.sub('ğ', 'g', val)
#         val = re.sub('ł', 'l', val)
#         val = re.sub('Ł', 'L', val)
#         val = re.sub('ō', 'o', val)
#         val = re.sub('Ō', 'O', val)
#         val = re.sub('ő', 'o', val)
#         val = re.sub('ř', 'r', val)
#         val = re.sub('ş', 's', val)
#         val = re.sub('Ş', 'S', val)
#         val = re.sub('š', 's', val)
#         val = re.sub('Š', 'S', val)
#         val = re.sub('ť', 't', val)
#         val = re.sub('ū', 'u', val)
#         val = re.sub('ů', 'u', val)
#         val = re.sub('ź', 'z', val)
#         val = re.sub('Ż', 'Z', val)
#         val = re.sub('ż', 'z', val)
#         val = re.sub('Ž', 'Z', val)
#         val = re.sub('ž', 'z', val)
#         val = re.sub('ư', 'u', val)
#         val = re.sub('ό', 'o', val)
#         val = re.sub('ạ', 'a', val)
#         val = re.sub('ả', 'a', val)
#         val = re.sub('ấ', 'a', val)
#         val = re.sub('ầ', 'a', val)
#         val = re.sub('ế', 'e', val)
#         val = re.sub('ề', 'e', val)
#         val = re.sub('ể', 'e', val)
#         val = re.sub('ỉ', 'i', val)
#         val = re.sub('ố', 'p', val)
#         val = re.sub('ồ', 'p', val)
#         val = re.sub('ớ', 'p', val)
#         val = re.sub('ợ', 'p', val)
#         val = re.sub('ứ', 'u', val)
#         val = re.sub('–', '-', val)
#         val = re.sub('‚', ',', val)
#         val = re.sub('“', '"', val)
#         val = re.sub('”', '"', val)
#         val = re.sub('⅔', '2/3', val)
#         val = re.sub('⅛', '1/8', val)
#         val = re.sub('∓', '+-', val)
#         val = re.sub('≈', '=', val)
#         val = val.strip()
#         val = re.sub(r'\s+', ' ', val)
#         entries[i_entry][i_val] = val
# # reduce dataset to those bits we care about
# _entries = {}
# for entry in entries:
#     if entry == ['']:
#         continue
#     assert len(entry) == 5, entry
#     if entry[headers['Poem']] == '' or entry[headers['Title']] == '':
#         continue
#     _entries[entry[headers['Title']]] = entry[headers['Poem']]
# entries = _entries
# # possibly shorten entries to 1-2 sentences, method = ?
# #   crop after 2 at most sentences (sentence delimitation of poetry is not very good)
# #   break poem into multiple shorter chunks with the same title
# # write output file
# f = open('../raw_data_sources/PoetryFoundationData.yaml', 'w')
# f.write(yaml.dump(entries))
# f.close()
# import encode
# encode.encode_json_to_AI_flavor([], '../encoded_data_sources/PoetryFoundationData.txt', extra_flavor='../raw_data_sources/PoetryFoundationData.yaml')




## compare encoded idx_to_token
# j_flavor = {"idx_to_token": {"1": "\"", "2": "B", "3": "r", "4": "i", "5": "m", "6": "s", "7": " ", "8": "a", "9": "o", "10": "n", "11": "e", "12": ",", "13": "M", "14": "d", "15": "w", "16": "y", "17": "b", "18": "t", "19": "\u2460", "20": "T", "21": "h", "22": "c", "23": "p", "24": "f", "25": "g", "26": "l", "27": ".", "28": "\n", "29": "R", "30": "u", "31": "D", "32": "k", "33": "+", "34": "\u24ea", "35": "\u225a", "36": "\u2259", "37": "v", "38": "A", "39": "P", "40": "W", "41": "?", "42": "I", "43": "G", "44": "U", "45": "C", "46": "\u21b5", "47": "-", "48": "S", "49": "!", "50": "'", "51": "1", "52": "9", "53": "6", "54": "J", "55": ":", "56": "H", "57": "Y", "58": ";", "59": "O", "60": "*", "61": "L", "62": "x", "63": "z", "64": "E", "65": "2", "66": "j", "67": "N", "68": "F", "69": "q", "70": "V", "71": "/", "72": "K", "73": "X", "74": "\u00c6", "75": "Q", "76": "Z", "77": "[", "78": "]", "79": "\u2026", "80": "0", "81": "5", "82": "3", "83": "8", "84": "\u00c4", "85": "(", "86": ")", "87": "\u2015", "88": "7", "89": "\u0153", "90": "4", "91": "\u00e8", "92": "\u0336", "93": "&", "94": "%", "95": "\u02dd", "96": "_", "97": "\u00ea", "98": "\u2122", "99": "\u00a1", "100": "#", "101": "|", "102": "=", "103": "\\", "104": "@", "105": "$", "106": "\u2295", "107": "<", "108": "\u012b", "109": ">", "110": "\u00b0", "111": "\u00b2", "112": "\u201e", "113": "^", "114": "\u00e4", "115": "{", "116": "}"}, "token_to_idx": {" ": 7, "\u225a": 35, "$": 105, "(": 85, ",": 12, "0": 80, "\u21b5": 46, "4": 90, "\u0336": 92, "8": 83, "<": 107, "@": 104, "D": 31, "H": 56, "L": 61, "P": 39, "T": 20, "X": 73, "\\": 103, "\u2460": 19, "d": 14, "h": 21, "l": 26, "p": 23, "t": 18, "x": 62, "|": 101, "#": 100, "'": 50, "+": 33, "/": 71, "\u00b0": 110, "3": 82, "7": 88, ";": 58, "?": 41, "C": 45, "\u00c4": 84, "G": 43, "K": 72, "O": 59, "S": 48, "\u2122": 98, "W": 40, "[": 77, "_": 96, "c": 22, "\u00e4": 114, "g": 25, "\u00e8": 91, "k": 32, "&": 93, "o": 9, "s": 6, "w": 15, "{": 115, "\n": 28, "\u2259": 36, "\u2295": 106, "\u201e": 112, "\u00a1": 99, "\"": 1, "\u2026": 79, "*": 60, ".": 27, "2": 65, "6": 53, ":": 55, ">": 109, "B": 2, "F": 68, "J": 54, "N": 67, "R": 29, "V": 70, "Z": 76, "\u02dd": 95, "^": 113, "b": 17, "f": 24, "j": 66, "n": 10, "r": 3, "v": 37, "z": 63, "\u00ea": 97, "\u2015": 87, "!": 49, "%": 94, ")": 86, "\u012b": 108, "-": 47, "1": 51, "\u00b2": 111, "5": 81, "9": 52, "=": 102, "A": 38, "E": 64, "\u00c6": 74, "I": 42, "M": 13, "Q": 75, "\u0153": 89, "U": 44, "Y": 57, "]": 78, "a": 8, "e": 11, "i": 4, "\u24ea": 34, "m": 5, "q": 69, "u": 30, "y": 16, "}": 116}}
# j_poems = {"idx_to_token": {"1": "!", "2": " ", "3": "k", "4": "a", "5": "t", "6": "y", "7": "\u2460", "8": "i", "9": "w", "10": "n", "11": "o", "12": "b", "13": "e", "14": "f", "15": "r", "16": "d", "17": "s", "18": "h", "19": "l", "20": "g", "21": "u", "22": "c", "23": "p", "24": "m", "25": "v", "26": "\"", "27": ",", "28": "(", "29": ")", "30": "j", "31": "C", "32": "J", "33": "F", "34": "\n", "35": "D", "36": "W", "37": "I", "38": ".", "39": "T", "40": "1", "41": "A", "42": ";", "43": "z", "44": "M", "45": "-", "46": "9", "47": "7", "48": "?", "49": "H", "50": "E", "51": "B", "52": "G", "53": "Y", "54": "L", "55": "R", "56": "N", "57": "O", "58": "q", "59": "x", "60": "S", "61": "2", "62": "0", "63": "P", "64": ":", "65": "6", "66": "3", "67": "X", "68": "V", "69": "Q", "70": "U", "71": "'", "72": "[", "73": "]", "74": "\u00ea", "75": "#", "76": "4", "77": "&", "78": "\u0153", "79": "\u24ea", "80": "\u225a", "81": "\u2259", "82": "/", "83": "K", "84": "8", "85": "5", "86": "\u00e8", "87": "*", "88": "\u2026", "89": "\u2296", "90": "$", "91": "Z", "92": "\u00b0", "93": "+", "94": "\u2022", "95": "=", "96": "{", "97": "\u00e4", "98": "%", "99": "\\", "100": "\u0301", "101": "\u0327", "102": "\u00c6", "103": "}", "104": "\u00a1", "105": "_", "106": "\u2213", "107": "\u0304", "108": "|", "109": "<", "110": ">", "111": "@", "112": "\u012b", "113": "\u2122", "114": "\u2295", "115": "\u0308", "116": "^", "117": "\u0303"}, "token_to_idx": {" ": 2, "Z": 91, "$": 90, "(": 28, ",": 27, "0": 62, "4": 76, "8": 84, "<": 109, "@": 111, "D": 35, "H": 49, "L": 54, "P": 63, "T": 39, "X": 67, "\\": 99, "\u2460": 7, "d": 16, "h": 18, "l": 19, "p": 23, "t": 5, "x": 59, "|": 108, "\u0301": 100, "\u2213": 106, "#": 75, "'": 71, "+": 93, "/": 82, "\u00b0": 92, "3": 66, "7": 47, ";": 42, "?": 48, "C": 31, "G": 52, "K": 83, "O": 57, "S": 60, "\u2022": 94, "W": 36, "[": 72, "_": 105, "c": 22, "\u00e4": 97, "g": 20, "\u00e8": 86, "k": 3, "\u2026": 88, "o": 11, "s": 17, "w": 9, "{": 96, "\u0304": 107, "\u0308": 115, "\n": 34, "Y": 53, "\u2295": 114, "\u00a1": 104, "\"": 26, "&": 77, "*": 87, ".": 38, "2": 61, "6": 65, ":": 64, ">": 110, "B": 51, "F": 33, "J": 32, "N": 56, "R": 55, "V": 68, "\u225a": 80, "^": 116, "b": 12, "f": 14, "\u2122": 113, "j": 30, "n": 10, "r": 15, "v": 25, "z": 43, "\u0303": 117, "\u24ea": 79, "\u2296": 89, "!": 1, "%": 98, "\u0327": 101, ")": 29, "\u012b": 112, "-": 45, "1": 40, "5": 85, "9": 46, "=": 95, "A": 41, "E": 50, "\u00c6": 102, "I": 37, "M": 44, "Q": 69, "\u0153": 78, "U": 70, "\u2259": 81, "]": 73, "a": 4, "e": 13, "i": 8, "\u00ea": 74, "m": 24, "q": 58, "u": 21, "y": 6, "}": 103}}
# for idx, char in j_poems['idx_to_token'].items():
#     if char not in j_flavor['token_to_idx']:
#         print('--A--', repr(char))
# for idx, char in j_flavor['idx_to_token'].items():
#     if char not in j_poems['token_to_idx']:
#         print('--B--', repr(char))


# ## compare chars in txt files
# f = open('../encoded_data_sources/PoetryFoundationData.txt')
# poems = set(f.read())
# f.close
# f = open('../encoded_data_sources/flavor.txt')
# flavor = set(f.read())
# f.close
# a = []
# for char in poems:
#     if char not in flavor:
#         print('--A--', char)
#         a.append(char)
# for char in flavor:
#     if char not in poems:
#         print('--B--', char)



## look for reminder text in main_text.txt
f = open('../encoded_data_sources/main_text.txt')
f_con = f.read()
f.close()
data = defaultdict(lambda: defaultdict(int))
for line in f_con.split('\n'):
    parenthesized = re.search(r'\([^\)]*?\)', line)
    if parenthesized is not None:
        data[parenthesized.group(0)][line] += 1
data2 = []
for k, v in data.items():
    sub_lists = sorted([[b, a] for a, b in v.items()], reverse=True)
    count = sum([a for a, b in sub_lists])
    data2.append((count, k, sub_lists))
data2.sort(reverse=True)
for count, k, sub_lists in data2:
    print(f'{count} -> "{k}"')
    for sub_count, s in sub_lists:
        print(f'\t{sub_count} -> "{s}"')

