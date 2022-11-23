import argparse
import json
import re

from matplotlib import pyplot as plt
from collections import defaultdict


parser = argparse.ArgumentParser()
parser.add_argument('--json_path', type=str,)
args = parser.parse_args()

with open(args.json_path) as f:
    j = json.load(f)


plt.plot(j['train_loss_history_key'], j['train_loss_history_val'], c='green', label='training loss')
plt.plot(j['val_loss_history_key'], j['val_loss_history_val'], c='red', label='validation loss')
plt.legend(loc=2)
plt.twinx()
plt.plot(j['learning_rate_history_key'], j['learning_rate_history_val'], marker='x', c='blue', label='learning rate')
plt.legend(loc=1)
plt.title(args.json_path)
plt.show()
