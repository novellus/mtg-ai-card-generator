import argparse
import json
import os
import re

from matplotlib import pyplot as plt
from collections import defaultdict


parser = argparse.ArgumentParser()
parser.add_argument('--path', type=str,)
args = parser.parse_args()


data = defaultdict(list)
args.path = os.path.join(args.path, 'textual_inversion_loss.csv')
with open(args.path) as f:
    f_con = f.read()
    lines = f_con.split('\n')
    headers = lines[0].split(',')
    headers = {h:i for i,h in enumerate(headers)}

    for line in lines[1:]:
        line = line.strip()
        if line:
            vals = line.split(',')
            for h,i in headers.items():
                data[h].append(float(vals[i]))


# step,epoch,epoch_step,loss,learn_rate
plt.plot(data['step'], data['loss'], c='green', label='training loss')
plt.legend(loc=2)
plt.twinx()
plt.plot(data['step'], data['learn_rate'], marker='x', c='blue', label='learning rate')
plt.legend(loc=1)
plt.title(args.path)
plt.show()
