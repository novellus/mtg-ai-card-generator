# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import json
import math
import os
import six
import numpy as np
import h5py
import codecs
import random


parser = argparse.ArgumentParser()
parser.add_argument('--input_txt', default='data/tiny-shakespeare.txt')
parser.add_argument('--output_h5', default='data/tiny-shakespeare.h5')
parser.add_argument('--output_json', default='data/tiny-shakespeare.json')
parser.add_argument('--chunk_delimiter', type=str, default='\n')
parser.add_argument('--val_frac', type=float, default=0.1)
parser.add_argument('--test_frac', type=float, default=0.1)
parser.add_argument('--quiet', action='store_true')
parser.add_argument('--encoding', default='utf-8')
parser.add_argument('--coerce_to', type=str, default=None)
args = parser.parse_args()


def stabilize_shuffle():
    # This should give a random but consistent ordering, to make comparing changes
    # between the output of different versions easier.
    random.seed(1371367)


def str_to_idx_array(s, dtype):
  l = len(s)
  if args.coerce_to is not None:
    l = 0
    for char in s:
      if char in token_to_idx:
        l += 1

  # returns np array of encoded string
  ret = np.zeros(l, dtype=dtype)

  i = 0
  for char in s:
    if char not in token_to_idx and args.coerce_to is not None:
      continue
    ret[i] = token_to_idx[char]
    i += 1

  return ret


if __name__ == '__main__':
  if args.encoding == 'bytes': args.encoding = None

  # First go the file once to see how big it is and to build the vocab
  token_to_idx = {}
  total_size = 0
  with codecs.open(args.input_txt, 'r', args.encoding) as f:
    for line in f:
      total_size += len(line)
      for char in line:
        if char not in token_to_idx:
          token_to_idx[char] = len(token_to_idx) + 1
  if args.coerce_to is not None:
    with open(args.coerce_to) as f:
      j = json.load(f)
      token_to_idx = {k:int(v) for k,v in j['token_to_idx'].items()}

  # Choose the datatype based on the vocabulary size
  dtype = np.uint8
  dtype_str = '8'
  if len(token_to_idx) > 255:
    dtype = np.uint32
    dtype_str = '32'

  # chunk data
  data = ''
  with codecs.open(args.input_txt, 'r', args.encoding) as f:
    data = f.read().strip()
  chunks = [chunk.strip() for chunk in data.split(args.chunk_delimiter) if chunk.strip()]
  n_chunks = len(chunks)
  max_len = max([len(x) for x in chunks])
  avg_len = int(math.ceil(sum([len(x) for x in chunks]) / float(n_chunks)))

  # randomize data order, before assigning chunks
  stabilize_shuffle()
  random.shuffle(chunks)

  # Now we can figure out the split sizes, in chunks
  val_n_chunks = int(args.val_frac * n_chunks)
  test_n_chunks = int(args.test_frac * n_chunks)
  train_n_chunks = n_chunks - val_n_chunks - test_n_chunks

  # assign chunks
  train = [chunk for (i_chunk, chunk) in enumerate(chunks) if                                  i_chunk < train_n_chunks               ]
  val   = [chunk for (i_chunk, chunk) in enumerate(chunks) if train_n_chunks                <= i_chunk < train_n_chunks + val_n_chunks]
  test  = [chunk for (i_chunk, chunk) in enumerate(chunks) if train_n_chunks + val_n_chunks <= i_chunk                                ]

  assert len(train) == train_n_chunks
  assert len(val) == val_n_chunks
  assert len(test) == test_n_chunks

  # val_size = int(args.val_frac * total_size)
  # test_size = int(args.test_frac * total_size)
  # train_size = total_size - val_size - test_size

  # print statistics
  if not args.quiet:
    print('Total vocabulary size: %d' % len(token_to_idx))
    print('Total tokens in file: %d' % total_size)
    print('  Training n_chunks: %d' % train_n_chunks)
    print('  Val n_chunks: %d' % val_n_chunks)
    print('  Test n_chunks: %d' % test_n_chunks)
    print('  Longest chunk length: %d' % max_len)
    print('  Average chunk length: %d' % avg_len)
    print('Using dtype ', dtype)

  # Just load data into memory ... we'll have to do something more clever
  # for huge datasets but this should be fine for now
  # train = np.zeros(train_size, dtype=dtype)
  # val = np.zeros(val_size, dtype=dtype)
  # test = np.zeros(test_size, dtype=dtype)

  # # Go through the file again and write data to numpy arrays
  # splits = [train, val, test]
  # split_idx, cur_idx = 0, 0
  # with codecs.open(args.input_txt, 'r', args.encoding) as f:
  #   for line in f:
  #     for char in line:
  #       splits[split_idx][cur_idx] = token_to_idx[char]
  #       cur_idx += 1
  #       if cur_idx == splits[split_idx].size:
  #         split_idx += 1
  #         cur_idx = 0

  # Write data to HDF5 file
  with h5py.File(args.output_h5, 'w') as f:
    # index chunks starting at 1, for ease of use in target language (lua)
    for i, c in enumerate(train):
      f.create_dataset('train/' + str(i + 1), data=str_to_idx_array(c, dtype))

    for i, c in enumerate(val):
      f.create_dataset('val/' + str(i + 1), data=str_to_idx_array(c, dtype))

    for i, c in enumerate(test):
      f.create_dataset('test/' + str(i + 1), data=str_to_idx_array(c, dtype))

    f.create_dataset('chunk_delimiter', data=str_to_idx_array(args.chunk_delimiter, dtype))
    f.create_dataset('train_vector', data=str_to_idx_array(args.chunk_delimiter.join(train), dtype))
    f.create_dataset('val_vector', data=str_to_idx_array(args.chunk_delimiter.join(val), dtype))
    f.create_dataset('test_vector', data=str_to_idx_array(args.chunk_delimiter.join(test), dtype))

  # For 'bytes' encoding, replace non-ascii characters so the json dump
  # doesn't crash
  if args.encoding is None:
    new_token_to_idx = {}
    for token, idx in six.iteritems(token_to_idx):
      if ord(token) > 127:
        new_token_to_idx['[%d]' % ord(token)] = idx
      else:
        new_token_to_idx[token] = idx
    token_to_idx = new_token_to_idx

  # Dump a JSON file for the vocab
  json_data = {
    'token_to_idx': token_to_idx,
    'idx_to_token': {v: k for k, v in six.iteritems(token_to_idx)},
    # 'dtype': dtype_str,
  }
  with open(args.output_json, 'w') as f:
    json.dump(json_data, f)
