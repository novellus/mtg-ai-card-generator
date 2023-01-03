import json
import os
import pprint
import re
import requests
import sys
import time

src = '../raw_data_sources/unique-artwork.json'
dest = '../raw_data_sources/mtg_art'  # art will be dowloaded to files in this folder

f = open(src)
f_con = f.read()
f.close()
j = json.loads(f_con)

os.makedirs(dest, exist_ok=True)

# make sure resolved filenames and extracted art are unique
uids = set()


def extract_art(j):
    # extract uri for art-cropped image, and download that image

    assert 'image_uris' in j, pprint.pformat(j)
    assert 'art_crop' in j['image_uris'], pprint.pformat(j)
    assert 'name' in j, pprint.pformat(j)
    # assert 'illustration_id' in j, pprint.pformat(j)  # this attribute isn't unique, apparently

    uri = j['image_uris']['art_crop']
    # print(uri)

    s = re.search(r'([a-zA-Z0-9\-_\/]+)(?:\.(png|jpg))', uri)
    assert s is not None, uri
    uid = s.group(1)
    uid = re.sub(r'\/', '_', uid)  # sanatize
    uid = re.sub(r'^io_art_crop_', '', uid)  # simplify
    # print(uid)

    ext = s.group(2)

    # check uniqueness
    assert uid not in uids, pprint.pformat(j)
    uids.add(uid)

    # download image from scryfall
    dest_path = os.path.join(dest, f'{uid}.{ext}')
    if not os.path.exists(dest_path):
        # mind scryfall's API usage rate limit: https://scryfall.com/docs/api
        time.sleep(0.15)
        img = requests.get(uri).content
        f = open(dest_path, 'wb')
        f.write(img)
        f.close()

    # extract card/face name into a caption file for the embedding preprocessor
    caption = j['name']
    dest_path = os.path.join(dest, f'{uid}.txt')
    f = open(dest_path, 'w')
    f.write(caption)
    f.close()


# process input dataset
# some cards have faces, some do not, and sometimes the image uris are / are-not stored there
num_cards = len(j)
for i_card, card in enumerate(j):
    print(f'Processing card {i_card + 1} / {num_cards}')
    found_image = False

    if 'image_uris' in card:
        extract_art(card)
        found_image = True
    if 'card_faces' in card:
        for face in card['card_faces']:
            if 'image_uris' in face:
                extract_art(face)
                found_image = True

    assert found_image, pprint.pformat(card)

