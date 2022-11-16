# Project Overview
* Autogenerates MTG cards
* 4 separate AIs contribute to the card design
    * &#x1F534; TODO ```name-generator``` is an LSTM trained to create card names. This was trained both on all exisitng MTG card names as well as on a smattering of of other words, phrases, and name-like strings. This increases the diversity of names outside of normal MTG card names.
    * &#x1F534; TODO ```main-text-generator``` is an LSTM trained to create all functional attributes and text of the cards. This was trained on all existing MTG card attributes + texts. This AI is whispered the names generated by the ```name-generator``` during sampling.
    * &#x1F534; TODO ```flavor-text-generator``` is an LSTM (&#x1F534; TODO is it?) trained to create flavor text for the cards. &#x1F534; TODO On what data is this trained? What inputs does it use? Etc.
    * &#x1F534; TODO ```image-generator``` is a stable diffusion model trained by the CompVis open source project to create images from text-based descriptions. This model is adapted from the CompVis open source project, and would be much to resource intensive to train from scratch on a hobbyist rig. This model uses the card name, along with some static descriptors to generate the images for the cards.
* The AI's are trained independently, and sampling is wrapped by ```master-generator```, which pulls all the ingredients together to create new cards.


# git-subtree management
* subtree list, with changes made to each repo
    * [torch-rnn](https://github.com/jcjohnson/torch-rnn) with some modifications inspired by [mtg-rnn](https://github.com/billzorn/mtg-rnn)
        * Created environment.yaml for python portion of the environment
        * Implemented whispering during sampling
        * &#x1F534; TODO Updated DataLoader to optionally accept a zero test fraction
        * Updated preprocessor to
            * partition input data on specified delimeter (eg between encoded cards)
            * randomize the chunk order
            * and assign a fraction of those chunks to training, validation, and testing; instead of assigning a fraction of raw data
            * store the data as processed chunks, which can be order randomized during batching
        * &#x1F534; TODO Updated DataLoader to
            * accept data chunks instead of raw data from the new proprocessing script
            * dynamically randomize the order of the chunks each epoch, and the batch locality of each chunk
            * and assign a fraction of those chunks to each batch; instead of assigning a fraction of raw data
        * &#x1F534; TODO Added option to DataLoader to dynamically randomize the order of structured content in encoded mtg cards in each batch
            * symbols in mana costs
            * order of unordered fields in a card (eg when the fields are specified by label rather than by order)
        * &#x1F534; TODO Updated sampler to optionally save output to specified file instead of printing to console
    * [mtgencode](https://github.com/Parrotapocalypse/mtgencode)
        * Created environment.yaml for conda management
        * Fixed reserved word ```set``` inappropriately used
        * Added printline stats during parsing wehen verbose is specified
        * Fixed rarity parsing error
        * Added sticker type cards and planechase type sets to exclude by default list
        * Added support for energy costs
        * Fixed card name encoding on double sided cards, stripped reverse card name from card title
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
    * Download ```AllPrintings.json``` from [mtgjson website](http://mtgjson.com/) to ```mtgencode/data```
    * Encode data
        * ```python encode.py -r -e named data/AllPrintings.json ../encoded_data_sources/main_text.txt```
        * ```python encode_2.py data/AllPrintings.json --outfile_names ../encoded_data_sources/names.txt --outfile_flavor ../encoded_data_sources/flavor.txt --outfile_artists ../encoded_data_sources/artists_stats.txt```
        * &#x1F534; TODO Add extra names and flavor
* torch-rnn
    * Setup torch dev environment. Conda doesn't handle lua / torch very well. Lua-torch is no longer maintained, and we can't use an old cuda installation on newer cards, so just install torch globally and fiddle until it works. The order of these steps is critical.
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
        * ```git clone https://github.com/torch/distro.git ~/torch --recursive```
            <!-- * &#x1F534; TODO (pick one) ```git clone https://github.com/nagadomi/distro.git ~/torch --recursive``` -->
            * ```cd ~/torch```
            * edit ```install-deps```
                * line 178 ```python-software-properties``` -> ```python3-software-properties```
                * line 202 ```ipython``` -> ```ipython3```
            * edit ```install.sh```
                * comment out everything inside of the conditionals on ```path_to_nvcc```
            * purge FindCuda from torch cmake ```rm -fr cmake/3.6/Modules/FindCUDA*```
            * ```./clean.sh```
            * ```export TORCH_NVCC_FLAGS="-D__CUDA_NO_HALF_OPERATORS__"```
            * ```bash install-deps```
            * ```./install.sh```
            * ```source ~/.bashrc```
            * ```CC=gcc-6 CXX=g++-6 ~/torch/install/bin/luarocks install torch```
            * ```CC=gcc-6 CXX=g++-6 ~/torch/install/bin/luarocks install nn```
            * ```CC=gcc-6 CXX=g++-6 ~/torch/install/bin/luarocks install optim```
            * ```CC=gcc-6 CXX=g++-6 ~/torch/install/bin/luarocks install lua-cjson```
            * patch and install cutorch
                * ```git clone https://github.com/torch/cutorch.git ~/torch/cutorch```
                * ```cp atomic.patch ~/torch/cutorch/.``` (duplicate atomic definition)
                * ```cp cutorch_init.patch ~/torch/cutorch/.``` (init)
                * ```patch -p1 < atomic.patch```
                * ```patch -p1 < cutorch_init.patch```
                * ```cd ~/torch/cutorch```
                * ```CC=gcc-6 CXX=g++-6 ~/torch/install/bin/luarocks make rocks/cutorch-scm-1.rockspec```
            * patch and install cunn
                * ```git clone https://github.com/torch/cunn.git ~/torch/cunn```
                * ```cp sparselinear.patch ~/torch/cunn/.``` (remove sparse matrices)
                * ```cp lookuptable.patch ~/torch/cunn/.``` (LookupTable)
                * ```cd ~/torch/cunn```
                * ```patch -p1 < sparselinear.patch```
                * ```patch -p1 < lookuptable.patch```
                * ```CC=gcc-6 CXX=g++-6 ~/torch/install/bin/luarocks make rocks/cunn-scm-1.rockspec```
            * install torch-hdf5
                * ```git clone https://github.com/deepmind/torch-hdf5 ~/torch/torch-hdf5```
                * ```cd ~/torch/torch-hdf5```
                * ```CC=gcc-6 CXX=g++-6 ~/torch/install/bin/luarocks make hdf5-0-0.rockspec```
    * preprocess data sets
        * ```python scripts/preprocess.py --input_txt ../encoded_data_sources/main_text.txt --output_h5 ../encoded_data_sources/main_text.h5 --output_json ../encoded_data_sources/main_text.json --test_frac 0```
        * ```python scripts/preprocess.py --input_txt ../encoded_data_sources/names.txt --output_h5 ../encoded_data_sources/names.h5 --output_json ../encoded_data_sources/names.json --test_frac 0```
        * ```python scripts/preprocess.py --input_txt ../encoded_data_sources/flavor.txt --output_h5 ../encoded_data_sources/flavor.h5 --output_json ../encoded_data_sources/flavor.json --test_frac 0```
* &#x1F534; TODO main repo
    * ```conda env create -f environment.yaml``` and then ```conda activate mtgencode```

# AI Training and Sampling
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
    * ```th train.lua -input_h5 ../encoded_data_sources/names.h5 -input_json ../encoded_data_sources/names.json -checkpoint_name ../nns/names/checkpoint```
    * ```th sample.lua -checkpoint ../nns/names/checkpoint_1000.t7```
* &#x1F534; TODO main repo


# Util
* ```watch -n1 nvidia-smi``` to see GPU resource utilization


# Prompt Development Tooling
* [Lexica](https://lexica.art/) and [OpenArt](https://openart.ai/) provide generated images and their prompts
* [img2prompt](https://replicate.com/methexis-inc/img2prompt) and [BLIP](https://huggingface.co/spaces/Salesforce/BLIP) predict the prompts for uploaded images
* etc: see [reddit tooling catalog](https://old.reddit.com/r/StableDiffusion/comments/xcq819/dreamers_guide_to_getting_started_w_stable/)

