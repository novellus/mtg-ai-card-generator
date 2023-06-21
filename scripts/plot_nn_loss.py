import argparse
import json
import os
import re

from generate_cards import resolve_folder_to_checkpoint_path

from matplotlib import pyplot as plt
from collections import defaultdict


parser = argparse.ArgumentParser()
parser.add_argument('--path', type=str, help='path to trained AI *.json, or a folder to autoselect longest trained AI therein')
args = parser.parse_args()

args.path = resolve_folder_to_checkpoint_path(args.path, ext='json')
with open(args.path) as f:
    f_con = f.read()
    j = json.loads(f_con)


plt.plot(j['train_loss_history_key'], j['train_loss_history_val'], c='green', label='training loss')
plt.plot(j['val_loss_history_key'], j['val_loss_history_val'], c='red', label='validation loss')
plt.legend(loc=2)
plt.twinx()
plt.plot(j['learning_rate_history_key'], j['learning_rate_history_val'], marker='x', c='blue', label='learning rate')
plt.legend(loc=1)
plt.title(args.path)
plt.show()
