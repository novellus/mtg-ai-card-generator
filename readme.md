# Project Overview
* Autogenerates MTG cards
* 4 separate AIs contribute to the card design
    * &#x1F534; TODO ```nns/names/*``` is an LSTM trained to create card names. This was trained both on all exisitng MTG card names as well as on a smattering of other words, phrases, and name-like strings. This increases the diversity of names outside of normal MTG card names.
    * &#x1F534; TODO ```nns/main-text/*``` is an LSTM trained to create all functional attributes and text of the cards. This was trained on select fields from select (most existing) MTG cards. This AI is whispered the names generated by the above AI during sampling.
    * &#x1F534; TODO ```nns/flavor/*``` is an LSTM trained to create flavor text for the cards. This was trained on the name and flavor text from select (most existing) MTG cards.
    * ```stable-diffusion``` is a stable diffusion model trained by the CompVis open source project to create images from text-based descriptions. This model is adapted from the CompVis open source project, and would be much too resource intensive to train from scratch on a hobbyist rig. This model uses the card name, along with some static descriptors to generate the images for the cards.
* The AI's are trained independently, and sampling is wrapped by ```generate_cards.py```, which pulls all the ingredients together to create new cards.
* data structure
    * ```raw_data_sources``` include user inputs for AI training data. These are processed into ```encoded_data_sources``` via ```rebuild_data_sources.sh```, which utilizes ```mtgencode``` and ```torch-rnn```.
    * ```nns``` contains trained text-based neural networks
    * ```torch-rnn``` contains code for training and sampling the text neuranl networks
    * ```stable-diffusion``` contains self-contained trained imaging neural networks and associated code
    * ```install_torch.sh``` and ```torch_patches``` are only used during environment setup, described bewlow
    * ```outputs``` contain final cards, card sheets, and intermediate outputs from each AI and processing stage


# git-subtree management
* subtree list, with changes made to each repo
    * [torch-rnn](https://github.com/jcjohnson/torch-rnn) with some modifications inspired by [mtg-rnn](https://github.com/billzorn/mtg-rnn)
        * Created environment.yaml for python portion of the environment
        * Implemented whispering during sampling
        * Removed test fraction loading from DataLoader, which is unused, so that it can accept an empty test fraction
        * Updated preprocessor to
            * partition input data on specified delimeter (eg between encoded cards)
            * randomize the chunk order
            * and assign a fraction of those chunks to training, validation, and testing; instead of assigning a fraction of raw data
            * store the data as processed chunks, which can be order randomized during batching
        * Updated DataLoader to
            * accept data chunks instead of raw data from the new proprocessing script
            * dynamically randomize the order and batch locality of the chunks each epoch
        * Added option to DataLoader to dynamically randomize the order of structured content in encoded mtg cards in each batch
            * symbols in mana costs
            * card field order (other than the card name field, which is always the first field and treated as defining for the AI)
        * Added option to trainer to set validation / checkpoint at a whole number of epochs, to avoid resetting the neural network in the middle of an arbitrarily segmented stream
        * &#x1F534; TODO Updated trainer to load history and learning rate from checkpoints
        * &#x1F534; TODO Updated trainer to print learning rate each time its updated
        * &#x1F534; TODO (ever?) Updated DataLoader to assign a fraction of chunks to each batch; instead of assigning a fraction of raw data
    * [mtgencode](https://github.com/Parrotapocalypse/mtgencode)
        * Created environment.yaml for conda management
        * Fixed reserved word ```set``` inappropriately used
        * Added printline stats during parsing wehen verbose is specified
        * Fixed rarity parsing error
        * Added sticker type cards and planechase type sets to exclude by default list
        * Added support for energy costs
        * Fixed card name encoding on double sided cards: stripped reverse card name from card title
        * Fixed card name for alchemy cards: removed the extra text 'A-' prepended to the name
        * Added 2nd encoder for separate data outputs focused on names, flavor text, and artists
    * [stable-diffusion](https://github.com/CompVis/stable-diffusion.git)
        * [models from huggingface](https://huggingface.co/CompVis/stable-diffusion-v-1-4-original). Git does not support large files (5GB and 8GB), so these files are not committed to the repo.
        * [stable-diffusion/optimizedSD from basujindal](https://github.com/basujindal/stable-diffusion.git). Modified ```optimized_txt2img.py``` and ```optimized_img2img.py```
            * Added watermarker
            * cleaned up interfaces
            * Added fully specifiable output dir and filename options to samplers
        * Safety filter disabled
        * Watermarker disabled for very small images instead of crashing (only works for images at least ```256x256```)
* each subtree has a remote under the same name as the directory
* create remote: ```git remote add -f <name> <url>```
* add subtree: ```git subtree add --prefix <dir> <remote> <branch> --squash```
* pull subtree: ```git fetch <remote> <branch>``` and then ```git subtree pull --prefix <dir> <remote> <branch> --squash```


# Environment Setup
* stable diffusion
    * Download miniconda https://docs.conda.io/en/latest/miniconda.html. Enable install for all users , disable Register Miniconda as the system Python 3.9.
    * ```conda env create -f environment.yaml``` and then ```conda activate ldm```
    * download the [models from huggingface](https://huggingface.co/CompVis/stable-diffusion-v-1-4-original) to ```stable-diffusion/models/ldm/stable-diffusion-v1/```
    * Run the samplers once manually to finish setup. The first time the samplers are used, conda will download a bunch more dependancies (several GB).
    * If you want to later delete your environment for reinstallation, run ```conda env remove -n ldo```
* mtgencode
    * ```conda env create -f environment.yaml``` and then ```conda activate mtgencode```
    * Finish setting up ntlk ```python -m nltk.downloader all```
    * Download ```AllPrintings.json``` from [mtgjson website](http://mtgjson.com/) to ```raw_data_sources/.```
* torch-rnn
    * Setup torch dev environment. Conda doesn't handle lua / torch very well. Lua-torch is no longer maintained, and we can't use an old cuda installation on newer cards, so just install torch globally to ```~/torch``` and fiddle until it works. The order of these steps is critical. If you screw up, its often easier to ```rm -rf ~/torch``` and start over than try to recover.
    * install ```libhdf5-dev```
        * add ```deb [trusted=yes check-valid-until=no] http://dk.archive.ubuntu.com/ubuntu/ trusty main universe``` to ```/etc/apt/sources.list```
        * ```sudo apt update```
        * ```sudo apt-get install libhdf5-dev==1.8.11*```
        * ```sudo apt-mark hold libhdf5-dev``` to pin version
    * ```conda env create -f environment-python.yaml```. Use this enviropnment only for the preprocessing script
    * install the [nvidia cuda toolkit](https://developer.nvidia.com/cuda-toolkit)
    * install ```gcc-6``` and ```g++-6```, since the older torch repo + cuda combination only works with this version
        * add ```deb [trusted=yes] http://dk.archive.ubuntu.com/ubuntu/ bionic main universe``` to ```/etc/apt/sources.list```
        * ```sudo apt update```
        * ```sudo apt install gcc-6 g++-6```
    * soft link cuda to ```gcc-6``` and ```g++-6```
        * ```sudo ln -s /usr/bin/gcc-6 /usr/local/cuda/bin/gcc```
        * ```sudo ln -s /usr/bin/g++-6 /usr/local/cuda/bin/g++```
    * link missing cmake input ```sudo ln -s -T /usr/local/cuda-11.8/lib64/libcublas.so /usr/lib/x86_64-linux-gnu/libcublas_device.so```
    * add repo for outdated software dependancies ```sudo add-apt-repository ppa:ubuntuhandbook1/ppa``` and ```sudo apt-get update```
    * fix luarockspeck using outdated (unsupported) URLs, by forcing git to correct them on the fly
        * ```git config --global url."https://github.com/".insteadOf git@github.com```
        * ```git config --global url."https://".insteadOf git://```
    * ```pip install ipython```
    * purge and install latest cmake
        * ```sudo apt-get purge cmake```
        * ```cd ~```
        * ```git clone https://github.com/Kitware/CMake.git```
        * ```cd CMake```
        * ```./bootstrap; make; sudo make install```
    * install torch using ```bash install_torch.sh |& tee torch-install-log.txt```. There will be several prompts.
        <!-- * &#x1F534; TODO (pick one) ```git clone https://github.com/nagadomi/distro.git ~/torch --recursive``` -->
* &#x1F534; TODO main repo
    * ```conda env create -f environment.yaml``` and then ```conda activate mtg-ai-main```
    * ```bash rebuild_data_sources.sh```
    * &#x1F534; TODO Add extra names and flavor
    * &#x1F534; TODO install mtg fonts

# Usage / AI Training and Sampling
* stable diffusion
    * execute ```conda activate ldm``` at the berginning of each bash session
    * text to image sampling: ```python scripts/txt2img.py --seed -1 --ckpt models/ldm/stable-diffusion-v1/sd-v1-4.ckpt --plms --n_samples 1 --n_iter 1 --skip_grid --H 64 --W 64 --prompt <text>```
        * Height and width must be multiples of ```64```.
        * The watermarker only works if image size is at least ```256x256```
        * If your output is a jumbled rainbow mess your image resolution is set TOO LOW
        * Having too high of a CFG level will also introduce rainbow distortion, your CFG shouldn't be set above 20
        * It's recommended to have your prompts be at least 512 pixels in one dimension, or a 384x384 square at the smallest. Anything smaller will have heavy artifacting.
        * reducing ram utilization:
            * generate smaller images: ```--H 64``` and ```--W 64```
            * generate fewer images at once (smaller batches): ```--n_samples 1```, ```--n_iter 1```. If generating only one image, can also do ```--skip_grid```
                * ```--n_iter``` generates images in series, with relatively low impact to vram utilization
                * ```--n_samples``` generates images in parallel, with relatively high impact to vram utilization
                * ```--n_rows``` is actually the number of columns in the grid image and does not affect batching or number of images generated
            * use the vram-optimized scripts instead
* stable diffusion - vram-optimized
    * text to image sampling: ```python optimizedSD/optimized_txt2img.py --ckpt models/ldm/stable-diffusion-v1/sd-v1-4.ckpt --n_samples 1 --n_iter 1 --H 1152 --W 1152 --prompt <text>```
    * image to image sampling: ```python optimizedSD/optimized_img2img.py --ckpt models/ldm/stable-diffusion-v1/sd-v1-4.ckpt --n_samples 1 --n_iter 1 --turbo --H 1024 --W 1024 --init-img <path> --prompt <text>```
* torch-rnn
    * ```th train.lua -input_h5 ../encoded_data_sources/names.h5 -input_json ../encoded_data_sources/names.json -checkpoint_name ../nns/names/checkpoint -rand_chunks 1```
    * ```th train.lua -input_h5 ../encoded_data_sources/flavor.h5 -input_json ../encoded_data_sources/flavor.json -checkpoint_name ../nns/flavor/checkpoint -rand_chunks 1```
    * ```th train.lua -input_h5 ../encoded_data_sources/main_text.h5 -input_json ../encoded_data_sources/main_text.json -checkpoint_name ../nns/main_text/checkpoint -rand_mtg_fields 1 -rand_chunks 1```
    * ```th sample.lua -checkpoint ../nns/names/checkpoint_1000.t7 -length 50```
* &#x1F534; TODO main repo


# Util
* ```watch -n1 nvidia-smi``` to see GPU resource utilization
* [torch docs](https://github.com/torch/torch7/blob/master/doc/tensor.md)


# Prompt Development Tooling
* [Lexica](https://lexica.art/) and [OpenArt](https://openart.ai/) provide generated images and their prompts
* [img2prompt](https://replicate.com/methexis-inc/img2prompt) and [BLIP](https://huggingface.co/spaces/Salesforce/BLIP) predict the prompts for uploaded images
* etc: see [reddit tooling catalog](https://old.reddit.com/r/StableDiffusion/comments/xcq819/dreamers_guide_to_getting_started_w_stable/)

