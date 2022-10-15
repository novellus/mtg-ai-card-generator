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
    * [torch-rnn](https://github.com/jcjohnson/torch-rnn) modified with analogous changes from [mtg-rnn](https://github.com/billzorn/mtg-rnn)
        * &#x1F534; TODO Implemented whispering during sampling
        * &#x1F534; TODO batching script branched, updated to take advantage of known information content. Both branches are used for different parts of the project. The new batcher is designed to consume data from [mtgencode](https://github.com/billzorn/mtgencode) (serialized mtg card text):
            * batcher interprets the data as whole cards, and partitions cards between the splits instead of raw data chunks
            * batch card order is randomized
            * batcher randomizes the symbols in mana costs of cards, and the order of the fields in a card when the fields are specified by label rather than by order
    * [mtgencode](https://github.com/Parrotapocalypse/mtgencode) (used as-is)
        * &#x1F534; TODO Created environment.yaml for conda management
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
* stable diffusion (taken from readme in this subtree)
    * Download miniconda https://docs.conda.io/en/latest/miniconda.html. Enable install for all users , disable Register Miniconda as the system Python 3.9.
    * ```conda env create -f environment.yaml``` and then ```conda activate ldm```
    * download the [models from huggingface](https://huggingface.co/CompVis/stable-diffusion-v-1-4-original) to ```stable-diffusion/models/ldm/stable-diffusion-v1/```
    * Run the samplers once manually to finish setup. The first time the samplers are used, conda will download a bunch more dependancies (several GB).
    * If you want to later delete your environment for reinstallation, run ```conda env remove -n ldo```
* &#x1F534; TODO mtgencode
    * ```conda env create -f environment.yaml``` and then ```conda activate mtgencode```
    * Download ```AllPrintings.json``` from [mtgjson website](http://mtgjson.com/) to ```mtgencode/data```
    * Encode this data with ```python encode.py  -r -e named data/AllPrintings.json ../all_printings_encoded.txt```
* &#x1F534; TODO torch-rnn
* &#x1F534; TODO main repo

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
* &#x1F534; TODO torch-rnn
* &#x1F534; TODO mtgencode
* &#x1F534; TODO main repo


# Util
* ```watch -n1 nvidia-smi``` to see GPU resource utilization


# Prompt Development Tooling
* [Lexica](https://lexica.art/) and [OpenArt](https://openart.ai/) provide generated images and their prompts
* [img2prompt](https://replicate.com/methexis-inc/img2prompt) and [BLIP](https://huggingface.co/spaces/Salesforce/BLIP) predict the prompts for uploaded images
* etc: see [reddit tooling catalog](https://old.reddit.com/r/StableDiffusion/comments/xcq819/dreamers_guide_to_getting_started_w_stable/)

