import re

from matplotlib import pyplot as plt
from collections import defaultdict


parser = argparse.ArgumentParser()
parser.add_argument('--log_path', type=str,)
args = parser.parse_args()


data_training = defaultdict(list)
data_validation = defaultdict(list)

with open(args.log_path) as f:
    epoch = None
    for line in f:
        search_epoch_line = re.search(r'^Epoch ([\d\.]+) [^\n]* loss = ([\d\.]+)\s+$', line)
        search_val_line = re.search(r'^val_loss =\s+([\d\.]+)\s+$', line)
        if search_epoch_line:
            epoch = float(search_epoch_line.group(1))
            data_training['epoch'].append(epoch)
            data_training['loss'].append(float(search_epoch_line.group(2)))
        elif search_val_line:
            data_training['epoch'].append(epoch)
            data_training['loss'].append(float(search_val_line.group(1)))


plt.plot(data_training['epoch'], data_training['loss'], c='green', label='training loss')
plt.plot(data_validation['epoch'], data_validation['loss'], c='green', label='validation loss')
plt.legend()
plt.show()
