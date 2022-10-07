# Project Overview
* Autogenerates MTG cards
* 4 separate AIs contribute to the card design
    * ```name-generator``` is an LSTM trained to create card names. This was trained both on all exisitng MTG card names as well as on a smattering of of other words, phrases, and name-like strings. This increases the diversity of names outside of normal MTG card names.
    * ```main-text-generator``` is an LSTM trained to create all functional attributes and text of the cards. This was trained on all existing MTG card attributes + texts. This AI is whispered the names generated by the ```name-generator``` during sampling.
    * ```flavor-text-generator``` is an LSTM (&#x1F534; TODO is it?) trained to create flavor text for the cards. &#x1F534; TODO On what data is this trained? What inputs does it use? Etc.
    * ```image-generator``` is a stable diffusion model trained by the CompVis open source project to create images from text-based descriptions. This model is adapted from the CompVis open source project, and would be much to resource intensive to train from scratch on a hobbyist rig. This model uses the card name, along with some static descriptors to generate the images for the cards.
* The AI's are trained independently, and sampling is wrapped by ```master-generator```, which pulls all the ingredients together to create new cards.


# git-subtree management
* subtree list
	* [torch-rnn](https://github.com/jcjohnson/torch-rnn)
	    * &#x1F534; TODO modified with analogous changes from [billzorn's cousen-branch](https://github.com/billzorn/mtg-rnn)
	    * &#x1F534; TODO Sampling updated to specify specific substrings midsample (eg card names)
	    * &#x1F534; TODO batching script branched, updated to take advantage of known information content. Both branches are used for different parts of the project. The new batcher is designed to consume data from [billzorn/mtgencode](https://github.com/billzorn/mtgencode) (mtg card text):
	        * batcher interprets the data as whole cards, and partitions cards between the splits instead of raw data chunks
	        * batch card order is randomized
	        * batcher randomizes the symbols in mana costs of cards, and the order of the fields in a card if the field's identity is specified by label rather than by order
	* [mtgencode](https://github.com/billzorn/mtgencode.git) (used as-is)
	* [stable-diffusion](https://github.com/CompVis/stable-diffusion.git) 
	    * [models from huggingface](https://huggingface.co/CompVis/stable-diffusion-v-1-4-original). Git does not support large files (5GB and 8GB), so these files are not committed to the repo.
	    * &#x1F534; TODO Safety filter disabled
	    * &#x1F534; TODO Added (consistent) output dir and filename options to sampler
	    * &#x1F534; TODO Randomize seed when not specified
	    * Watermarker disabled for very small images instead of crashing (only works for images at least ```256x256```). This enables use at lower vram capacities.
* each subtree has a remote under the same name as the directory
* create remote: ```git remote add -f <dir> <url>```
* add subtree: ```git subtree add --prefix <dir> <remote> <branch> --squash```
* pull subtree: ```git fetch <remote> <branch>``` and then ```git subtree pull --prefix <dir> <remote> <branch> --squash```


# Environment Setup
* stable diffusion (taken from readme in this subtree)
    * Download miniconda https://docs.conda.io/en/latest/miniconda.html. Enable install for all users , disable Register Miniconda as the system Python 3.9.
    * ```conda env create -f environment.yaml```
    * ```conda activate ldm``` - &#x1F534; TODO Repeat each new shell session?
    * download the [models from huggingface](https://huggingface.co/CompVis/stable-diffusion-v-1-4-original) to ```stable-diffusion/models/ldm/stable-diffusion-v1/```
    * Run the samplers once manually to finish setup. The first time the samplers are used, conda will download a bunch more dependancies (several GB).
    * If you want to later delete your environment for reinstallation, run ```conda env remove -n ldo```
* &#x1F534; TODO torch-rnn
* &#x1F534; TODO mtgencode
* &#x1F534; TODO main repo

# AI Training and Sampling
* &#x1F534; TODO stable diffusion
    * text to image sampling: ```python scripts/txt2img.py --seed -1 --ckpt models/ldm/stable-diffusion-v1/sd-v1-4.ckpt --plms --H 64 --W 64 --prompt <text>```
    	* Height and width must be multiples of ```64```.
    	* The watermarker only works if image size is at least ```256x256```
    	* If your output is a jumbled rainbow mess your image resolution is set TOO LOW
    	* Having too high of a CFG level will also introduce rainbow distortion, your CFG shouldn't be set above 20
* &#x1F534; TODO torch-rnn
* &#x1F534; TODO mtgencode
* &#x1F534; TODO main repo
