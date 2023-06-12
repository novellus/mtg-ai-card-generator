GPTQ is a clever quantization algorithm that lightly reoptimizes the weights during quantization so that the accuracy loss is compensated relative to a round-to-nearest quantization. See the paper for more details: https://arxiv.org/abs/2210.17323

4-bit GPTQ models reduce VRAM usage by about 75%. So LLaMA-7B fits into a 6GB GPU, and LLaMA-30B fits into a 24GB GPU.

## Overview

There are two ways of loading GPTQ models in the web UI at the moment:

* Using AutoGPTQ:
  * supports more models
  * standardized (no need to guess any parameter)
  * is a proper Python library
  * ~no wheels are presently available so it requires manual compilation~
  * supports loading both triton and cuda models

* Using GPTQ-for-LLaMa directly:
  * faster CPU offloading
  * faster multi-GPU inference
  * supports loading LoRAs using a monkey patch
  * requires you to manually figure out the wbits/groupsize/model_type parameters for the model to be able to load it
  * supports either only cuda or only triton depending on the branch

For creating new quantizations, I recommend using AutoGPTQ: https://github.com/PanQiWei/AutoGPTQ

## AutoGPTQ

### Installation

No additional steps are necessary as AutoGPTQ is already in the `requirements.txt` for the webui. If you still want or need to install it manually for whatever reason, these are the commands:

```
conda activate textgen
git clone https://github.com/PanQiWei/AutoGPTQ.git && cd AutoGPTQ
pip install .
```

The last command requires `nvcc` to be installed (see the [instructions above](https://github.com/oobabooga/text-generation-webui/blob/main/docs/GPTQ-models-(4-bit-mode).md#step-1-install-nvcc)).

### Usage

When you quantize a model using AutoGPTQ, a folder containing a filed called `quantize_config.json` will be generated. Place that folder inside your `models/` folder and load it with the `--autogptq` flag:

```
python server.py --autogptq --model model_name
```

Alternatively, check the `autogptq` box in the "Model" tab of the UI before loading the model.

### Offloading

In order to do CPU offloading or multi-gpu inference with AutoGPTQ, use the `--gpu-memory` flag. It is currently somewhat slower than offloading with the `--pre_layer` option in GPTQ-for-LLaMA.

For CPU offloading:

```
python server.py --autogptq --gpu-memory 3000MiB --model model_name
```

For multi-GPU inference:

```
python server.py --autogptq --gpu-memory 3000MiB 6000MiB --model model_name
```

### Using LoRAs with AutoGPTQ

Not supported yet.

## GPTQ-for-LLaMa

GPTQ-for-LLaMa is the original adaptation of GPTQ for the LLaMA model. It was made possible by [@qwopqwop200](https://github.com/qwopqwop200/GPTQ-for-LLaMa): https://github.com/qwopqwop200/GPTQ-for-LLaMa

Different branches of GPTQ-for-LLaMa are currently available, including:

| Branch | Comment |
|----|----|
| [Old CUDA branch (recommended)](https://github.com/oobabooga/GPTQ-for-LLaMa/) | The fastest branch, works on Windows and Linux. |
| [Up-to-date triton branch](https://github.com/qwopqwop200/GPTQ-for-LLaMa) | Slightly more precise than the old CUDA branch from 13b upwards, significantly more precise for 7b. 2x slower for small context size and only works on Linux. |
| [Up-to-date CUDA branch](https://github.com/qwopqwop200/GPTQ-for-LLaMa/tree/cuda) | As precise as the up-to-date triton branch, 10x slower than the old cuda branch for small context size. |

Overall, I recommend using the old CUDA branch. It is included by default in the one-click-installer for this web UI.

### Installation

Start by cloning GPTQ-for-LLaMa into your `text-generation-webui/repositories` folder:

```
mkdir repositories
cd repositories
git clone https://github.com/oobabooga/GPTQ-for-LLaMa.git -b cuda
```

If you want to you to use the up-to-date CUDA or triton branches instead of the old CUDA branch, use these commands:

```
git clone https://github.com/qwopqwop200/GPTQ-for-LLaMa.git -b cuda
```

```
git clone https://github.com/qwopqwop200/GPTQ-for-LLaMa.git -b triton
```

Next you need to install the CUDA extensions. You can do that either by installing the precompiled wheels, or by compiling the wheels yourself.

### Precompiled wheels

Kindly provided by our friend jllllll: https://github.com/jllllll/GPTQ-for-LLaMa-Wheels

Windows:

```
pip install https://github.com/jllllll/GPTQ-for-LLaMa-Wheels/raw/main/quant_cuda-0.0.0-cp310-cp310-win_amd64.whl
```

Linux:

```
pip install https://github.com/jllllll/GPTQ-for-LLaMa-Wheels/raw/Linux-x64/quant_cuda-0.0.0-cp310-cp310-linux_x86_64.whl
```

### Manual installation

#### Step 1: install nvcc

```
conda activate textgen
conda install -c conda-forge cudatoolkit-dev
```

The command above takes some 10 minutes to run and shows no progress bar or updates along the way.

You are also going to need to have a C++ compiler installed. On Linux, `sudo apt install build-essential` or equivalent is enough.

If you're using an older version of CUDA toolkit (e.g. 11.7) but the latest version of `gcc` and `g++` (12.0+), you should downgrade with: `conda install -c conda-forge gxx==11.3.0`. Kernel compilation will fail otherwise.

#### Step 2: compile the CUDA extensions

```
cd repositories/GPTQ-for-LLaMa
python setup_cuda.py install
```

### Getting pre-converted LLaMA weights

These are models that you can simply download and place in your `models` folder.

* Converted without `group-size` (better for the 7b model): https://github.com/oobabooga/text-generation-webui/pull/530#issuecomment-1483891617
* Converted with `group-size` (better from 13b upwards): https://github.com/oobabooga/text-generation-webui/pull/530#issuecomment-1483941105 

⚠️ The tokenizer files in the sources above may be outdated. Make sure to obtain the universal LLaMA tokenizer as described [here](https://github.com/oobabooga/text-generation-webui/blob/main/docs/LLaMA-model.md#option-1-pre-converted-weights).

### Starting the web UI:

Use the `--gptq-for-llama` flag.

For the models converted without `group-size`:

```
python server.py --model llama-7b-4bit --gptq-for-llama 
```

For the models converted with `group-size`:

```
python server.py --model llama-13b-4bit-128g  --gptq-for-llama --wbits 4 --groupsize 128
```

The command-line flags `--wbits` and `--groupsize` are automatically detected based on the folder names in many cases.

### CPU offloading

It is possible to offload part of the layers of the 4-bit model to the CPU with the `--pre_layer` flag. The higher the number after `--pre_layer`, the more layers will be allocated to the GPU.

With this command, I can run llama-7b with 4GB VRAM:

```
python server.py --model llama-7b-4bit --pre_layer 20
```

This is the performance:

```
Output generated in 123.79 seconds (1.61 tokens/s, 199 tokens)
```

You can also use multiple GPUs with `pre_layer` if using the oobabooga fork of GPTQ, eg `--pre_layer 30 60` will load a LLaMA-30B model half onto your first GPU and half onto your second, or `--pre_layer 20 40` will load 20 layers onto GPU-0, 20 layers onto GPU-1, and 20 layers offloaded to CPU.

### Using LoRAs with GPTQ-for-LLaMa

This requires using a monkey patch that is supported by this web UI: https://github.com/johnsmith0031/alpaca_lora_4bit

To use it:

1. Clone `johnsmith0031/alpaca_lora_4bit` into the repositories folder:

```
cd text-generation-webui/repositories
git clone https://github.com/johnsmith0031/alpaca_lora_4bit
```

⚠️  I have tested it with the following commit specifically: `2f704b93c961bf202937b10aac9322b092afdce0`

2. Install https://github.com/sterlind/GPTQ-for-LLaMa with this command:

```
pip install git+https://github.com/sterlind/GPTQ-for-LLaMa.git@lora_4bit
```

3. Start the UI with the `--monkey-patch` flag:

```
python server.py --model llama-7b-4bit-128g --listen --lora tloen_alpaca-lora-7b --monkey-patch
```


