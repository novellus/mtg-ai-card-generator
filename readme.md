# Project Overview
* Autogenerates MTG cards
* 4 separate AIs contribute to the card design
    * ```nns/names*``` is an LSTM trained to create card names. This was trained both on all exisitng MTG card names as well as on a smattering of other words, phrases, and name-like strings. This increases the diversity of names outside of normal MTG card names.
    * ```nns/main-text*``` is an LSTM trained to create all functional attributes and text of the cards. This was trained on select fields from select (most existing) MTG cards. This AI is whispered the names generated by the above AI during sampling.
    * ```nns/flavor*``` is an LSTM trained to create flavor text for the cards. This was trained on the name and flavor text from select (most existing) MTG cards.
    * ```stable-diffusion``` is a stable diffusion model trained by the CompVis open source project to create images from text-based descriptions. This model is adapted from the CompVis open source project, and would be much too resource intensive to train from scratch on a hobbyist rig. This model uses the card name, along with some static descriptors to generate the images for the cards.
* The AI's are trained independently, and sampling is wrapped by ```generate_cards.py```, which pulls all the ingredients together to create new cards.
* data structure
    * ```raw_data_sources``` include user inputs for AI training data. These are processed into ```encoded_data_sources``` via ```rebuild_data_sources.sh```, which utilizes ```mtgencode``` and ```torch-rnn```.
    * ```nns``` contains trained text-based neural networks
    * ```torch-rnn``` contains code for training and sampling the text neural networks
    * ```stable-diffusion``` contains self-contained trained imaging neural networks and associated code
    * ```scripts``` contains the main generator entry point ```generate_cards.py``` as well as intermediary and utility scripts
    * ```outputs``` contains final cards, card sheets, and intermediate outputs from each AI and processing stage
    * ```image_templates``` contains template images for rendering the generated cards


# Workflow / Getting Started
* Run through the environment setup section below
* Train up some neural nets for names, flavor and main text. See the training section below.
* Finally, use the main generator ```generate_cards.py``` to sample the AIs, process + decode the raw data, and render the final cards.
* Optionally create card sheets for deckbuilding in Tabletop Simulator via ```build_sheets.py```


# Subtree List and their Customizations
* [torch-rnn](https://github.com/jcjohnson/torch-rnn) with some modifications inspired by [mtg-rnn](https://github.com/billzorn/mtg-rnn)
    * Created environment.yaml for python portion of the environment
    * Implemented whispering during sampling
    * Removed test fraction loading from DataLoader, which is unused, so that it can accept an empty test fraction
    * Updated preprocessor to
        * partition input data on specified delimeter (eg between encoded cards)
        * randomize the chunk order
        * and assign a fraction of those chunks to training, validation, and testing; instead of assigning a fraction of raw data
        * store the data as processed chunks, which can be order randomized during batching
    * stabalized shuffle order in preprocessor
    * Updated DataLoader to
        * accept data chunks instead of raw data from the new proprocessing script
        * dynamically randomize the order and batch locality of the chunks each epoch
    * Added option to DataLoader to dynamically randomize the order of structured content in encoded mtg cards in each batch
        * symbols in mana costs
        * card field order (other than the card name field, which is always the first field and treated as defining for the AI)
    * Added option to trainer to set validation / checkpoint at a whole number of epochs, to avoid resetting the neural network in the middle of an arbitrarily segmented stream
    * Updated trainer to load history and learning rate from checkpoints
    * Updated trainer to print learning rate each time its updated
    * Updated trainer to decouple checkpoint, validation, and learning rate decay frequencies from epochs / each other, and have CLI params for all
    * Updated trainer to not clear optim state each time the learning rate is changed, for smoother loss curves
    * Added seed input option to sampler for repeatable sampling
* [mtgencode](https://github.com/Parrotapocalypse/mtgencode)
    * Created environment.yaml for conda management
    * Fixed reserved word ```set``` inappropriately used
    * Added printline stats during parsing wehen verbose is specified
    * Fixed rarity parsing error
    * Added sticker type cards and planechase type sets to exclude by default list
    * Added support for energy costs
    * Fixed recognition and encoding of double sided cards: stripped reverse card name from card title and used newer json fields for proper card name and side
    * Fixed card name for alchemy cards: removed the extra text 'A-' prepended to the name
    * Added 2nd encoder for separate data outputs focused on names, flavor text, and artists
    * Modified decoder to accept input string on cli instead of file
    * added decoder ```out_encoding``` argument to fix bug when writing to stdout
    * Uncommented decoding steps so that it actually decodes all the encoded properties...
    * added ```to_json``` output option to decoder, and ```to_serializable``` functions for cards
    * fixed decoder decodes integer values as floats
* [stable-diffusion](https://github.com/CompVis/stable-diffusion.git)
    * [models from huggingface](https://huggingface.co/CompVis/stable-diffusion-v-1-4-original). Git does not support large files (5GB and 8GB), so these files are not committed to the repo.
    * [stable-diffusion/optimizedSD from basujindal](https://github.com/basujindal/stable-diffusion.git). Modified ```optimized_txt2img.py``` and ```optimized_img2img.py```
        * Added watermarker
        * cleaned up interfaces
        * Added fully specifiable output dir and filename options to samplers
        * Added negative prompt feature, per [AUTOMATIC1111's wiki](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Negative-prompt)
            * and added flag to slightly break negative weighting in interesting ways ```force_combined_prompt_weighting```
    * Safety filter disabled
    * Watermarker disabled for very small images instead of crashing (only works for images at least ```256x256```)
* each subtree has a remote under the same name as the directory
* create remote: ```git remote add -f <name> <url>```
* add subtree: ```git subtree add --prefix <dir> <remote> <branch> --squash```
* pull subtree: ```git fetch <remote> <branch>``` and then ```git subtree pull --prefix <dir> <remote> <branch> --squash```


# &#x1F534; TODOs
* renderer
    * limit mana render space to at most half the title bar
    * support planeswalkers
        * different frame?
        * loyalty increase / deccrease icons in main text box
        * loyalty box in lower right corner
    * add legendary frame
    * fix: title text without underhangs on the letters appears lower sitting than text that does (ie baseline is lower, and text is rendered larger)
    * decrease save file resolution to limit file size
* increment seed after each art generation so that the art isn't all similar
* statistics
* generate additional basic lands with custom / unique art
    * use unique type identifer (```Basic Land```?) to indicate usage of textless frames
        * may need to include text (or use colored frames) to identify the land color, since art will be hit or miss
    * add 2nd ```main_basics``` function for generating these basics
        * probably add an argument to specify prompt? Or use a standard set?
* configure txt2img args
    * consider adjusting the prompt to specify a specific style
    * find a way to not render actual magic card elements, like borders, titles, mana, etc
    * ```python optimizedSD/optimized_txt2img.py --ckpt models/ldm/stable-diffusion-v1/sd-v1-4.ckpt --outdir outputs/mtg_test --n_samples 1 --n_iter 5 --H 960 --W 768 --turbo --prompt "wall of the geist:1 mtg:-1 magic the gathering:-1" --force_combined_prompt_weighting```
        * uses slightly broken negative weighting
        * seems to produce card-like art instead of actual cards
        * seems to only work at higher resolution (512x512 produces images of cards). I think the higher resolution is slightly broken in the base repo, which when combined with the slightly broken negative weighting, somehow comes out on top, statistically
        * try to come up with args that eliminate cards while still enabling card-like art
    * ```python optimizedSD/optimized_txt2img.py --ckpt models/ldm/stable-diffusion-v1/sd-v1-4.ckpt --outdir outputs/mtg_test --n_samples 1 --n_iter 5 --H 960 --W 768 --turbo --prompt "wall of the geist:1 mtg:1 magic the gathering:1 text:-1 card frame:-1" --force_combined_prompt_weighting```
    * consider switching to [AUTOMATIC1111's fork](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API), which has several feature advantages over the base repo
        * textual inversion: train the neural network on mtg art, and encode a keyword
            * could gather mtg art images from skryfall: [bulk card data](https://scryfall.com/docs/api/bulk-data) and [imagery api](https://scryfall.com/docs/api/images)
        * high res fix or outpainting
        * proper negative prompts
        * prompt editing, if that proves useful for the odd style / name combinations
        * face restoration
        * png info
        * need to start /stop a local server to query for image data
* Add extra names and flavor
* finish training the AIs
* generate a small-medium batch of cards for Colin to review


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
    * install torch using ```bash install_torch.sh |& tee log-torch-install.txt```. There will be several prompts.
        <!-- * &#x1F534; TODO (pick one) ```git clone https://github.com/nagadomi/distro.git ~/torch --recursive``` -->
* main repo
    * ```conda env create -f environment.yaml``` and then ```conda activate mtg-ai-main```
    * ```bash rebuild_data_sources.sh |& tee log-data-build.txt```

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
    * ```mkdir -p ../nns/names && th train.lua -input_h5 ../encoded_data_sources/names.h5 -input_json ../encoded_data_sources/names.json -checkpoint_name ../nns/names/checkpoint -rand_chunks 1 -checkpoint_n_epochs 10 -validate_n_epochs 1 -print_every 1 -num_layers 3 -rnn_size 256 -max_epochs 1000 -batch_size 500 -seq_length 150 -dropout 0.1 -learning_rate 0.002 -lr_decay_n_epochs 3 -lr_decay_factor 0.98 |& tee -a ../nns/names/log.txt```
    * ```mkdir -p ../nns/flavor && th train.lua -input_h5 ../encoded_data_sources/flavor.h5 -input_json ../encoded_data_sources/flavor.json -checkpoint_name ../nns/flavor/checkpoint -rand_chunks 1 -checkpoint_n_epochs 10 -validate_n_epochs 1 -print_every 1 -num_layers 3 -rnn_size 256 -max_epochs 1000 -batch_size 200 -seq_length 750 -dropout 0.1 -learning_rate 0.002 -lr_decay_n_epochs 5 -lr_decay_factor 0.9 |& tee -a ../nns/flavor/log.txt```
    * ```mkdir -p ../nns/main_text && th train.lua -input_h5 ../encoded_data_sources/main_text.h5 -input_json ../encoded_data_sources/main_text.json -checkpoint_name ../nns/main_text/checkpoint -rand_chunks 1 -rand_mtg_fields 1 -checkpoint_n_epochs 10 -validate_n_epochs 1 -print_every 1 -num_layers 3 -rnn_size 400 -max_epochs 1000 -batch_size 100 -seq_length 1000 -dropout 0.1 -learning_rate 0.002 -lr_decay_n_epochs 3 -lr_decay_factor 0.99 |& tee -a ../nns/main_text/log.txt```
    * ```th sample.lua -checkpoint ../nns/names/checkpoint_1000.t7 -length 50```


# Util
* ```watch -n1 nvidia-smi``` to see GPU resource utilization
* [torch docs](https://github.com/torch/torch7/blob/master/doc/tensor.md)
* batch convert svg images to png ```find . -name "*.svg" | xargs inkscape --export-type=png --export-width=1000 --export-height=1000 --export-png-color-mode=RGBA_8 --batch-process```


# Prompt Development Tooling
* [Lexica](https://lexica.art/) and [OpenArt](https://openart.ai/) provide generated images and their prompts
* [img2prompt](https://replicate.com/methexis-inc/img2prompt) and [BLIP](https://huggingface.co/spaces/Salesforce/BLIP) predict the prompts for uploaded images
* etc: see [reddit tooling catalog](https://old.reddit.com/r/StableDiffusion/comments/xcq819/dreamers_guide_to_getting_started_w_stable/)

