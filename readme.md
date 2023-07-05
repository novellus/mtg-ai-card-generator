### MTG-AI-Generator: Autogenerate MTG cards end-to-end using AIs to write fields and create art.

# Project Overview
```scripts/generate_cards.py``` is the main entry point. This will
* sample AIs
* process + decode their raw data
* render the final cards as image files
* and finally save outputs in the specified folder


4 separate AIs contribute to the card design
* First an AI generates an arbitrary card name. Then the name is whispered to a second AI which generates the main text and all in play properties of the card. The name and type are prompted to a third AI which generates flavor text for the card. Finally, the name, type, and flavor text are prompted to a fourth AI to create visual art for the card.
* ```nns/names*``` is an LSTM created for this project and trained to generate card names. This was trained both on all exisitng MTG card names as well as on a smattering of other words, phrases, and name-like strings. This increases the diversity of names outside of normal MTG card names.
* ```nns/main_text*``` is an LSTM created for this project and trained to generate all functional attributes and text of the cards. This was trained on select fields from all MTG cards (at time of training). This AI is whispered the names generated by the above AI during sampling.
* Flavor text is written by an LLM, prompted by card name, card type, and some static descriptors. The model was originally created by Meta, then leaked to the public, and further trained and refined by many individuals. This is wrapped by an open-source web-UI at ```llm```.
* Card art is generated by stable diffusion, prompted by the card name, type, flavor text, and some static descriptors. The model was originally created by the CompVis open source project to create images from text-based descriptions, and then further trained and refined by many individuals. This is wrapped by an open-source web-UI at ```A1SD```.
* The AI's are trained independently, and sampling is wrapped by ```generate_cards.py```, which pulls all the ingredients together to create new cards.


# Workflow / Getting Started
* Run through the environment setup section below
* The main entry point for the project is ```scripts/generate_cards.py``` 
    * example command: ```python generate_cards.py --lstm_gpu 1 --names_nn ../nns/names_3 --main_text_nn ../nns/main_text_13 --flavor_nn timdettmers_guanaco-65b-merged --gpu-memory 23 --cpu-memory 250 --sd_nn "nov_mtg_art_v2_3.ckpt [76fcbf0ef5]" --outdir ../outputs --num_cards 10 --hr_upscale 2 --verbosity=9 --to_pdf```
        * This command takes about 2 hours to execute on the dev's machine
        * see ```python generate_cards.py --help``` for more info on arguments
    * AI samples are cached in subdirectories (```*_cache```) under the auto-generated output folder (eg ```../outputs/00003_481992436```), so the generator can be stopped and resumed without losing much via the ```--resume_folder ...``` argument. Also useful if it crashes for some inconsistent reason.
    * Statistics about generated cards are output to ```stats.yaml``` in the output folder
    * Full card text for all cards is output to ```card_data.yaml``` in the output folder
    * A printable pdf is generated (```printable_cards.pdf```) if you specify the ```--to_pdf``` arg
<!-- * Optionally create card sheets for deckbuilding in Tabletop Simulator via ```to_tts_asset.py```, or PDFs for printing via ```to_pdf.py```
    * these will compile all images in the output folder, so if you don't want to include all of them, remove the undesired files first
* Optionally, ```card_data.yaml``` can be manually edited (eg to fix AI-generated typos) by adding fields named ```*_override``` under card definition(s), and then ```scripts/render.py``` can be executed directly (see ```--help``` for more info) to re-render the cards with the manual modifications.
    * Similarly, the cached art under ```outputs/*/art_cache``` can be modified to change the card art before re-rendering. If this is the only change to a card, then delete the rendered card image file so the renderer will detect that it should be rendered. -->
* Overall timing

| args                                            | timing on the dev's machine | amount of data produced |
| ----------------------------------------------- | --------------------------- | ----------------------- |
| ```--hr_upscale 2``` (all features enabled)     | ~ 5-10 minutes per card     | ~ 5 MB / card           |
| ```--no_flavor --hr_upscale 2```                | ~ 2.5 cards / minute        | ~ 4.5 MB / card         |
| ```--no_flavor```                               | ~ 6.5 cards / minute        | ~ 2.5 MB / card         |
| ```--no_flavor --no_art```                      | ~ 10 cards / minute         | ~ 250 KB / card         |
| ```--no_flavor --no_art --no_render```          | ~ 20 cards / minute         | ~ 1.5 KB / card         |
| ```--to_pdf``` (ignoring other args + steps)    | Adds ~ 10s per card         | roughly doubles         |

* other run modes
    * generate basic lands with unique art: ```python generate_cards.py --sd_nn "nov_mtg_art_v2_3.ckpt [76fcbf0ef5]" --verbosity=9 --outdir ../outputs --hr_upscale 2 --basic_lands "{'Plains':51, 'Island':51, 'Swamp':51, 'Mountain':51, 'Forest':51, 'Snow-Covered Plains':25, 'Snow-Covered Island':25, 'Snow-Covered Swamp':25, 'Snow-Covered Mountain':25, 'Snow-Covered Forest':25, 'Wastes':36}" --to_pdf```
    * Quickly create card text, which can be hand-modified before rendering
        * Run ```generate_cards.py``` like normal plus args ```--no_flavor --no_art --no_render```, so that only the text is generated
        * Open the generated ```card_data.yaml```, and hand-modify the contents to your heart's desire. You can also delete cards entirely from the file.
        * Run ```generate_cards.py``` like normal with ```--finish_yaml <yaml path>```
    * resume an interupted generation with ```--resume_folder <folder path>``` (and specify the same args)


# &#x1F534; TODOs
* generate additional basic lands with custom / unique art
* finish yaml once colin down-selects
* low priorty (ie probably never)
    * add bypass to lstm parser where if max resamples are exceeded, instead of raising the error, it raises a unique error which is caught by ```generate_cards.py``` who loudly removes that card from the processing and finishes the rest of the cards
    * create ```to_tts_asset.py``` to format cards into sheets for upload to TTS
        * limit file size to something appropriate for TTS assets (40MB??)
    * ```render.py```
        * decrease save file resolution to limit file size?
        * render legendary frame?
        * refine txt2img args to furthr dissuade creating art images resembling mtg cards ?
        * set order of mana according to [this guide](https://cardboardkeeper.com/mtg-color-order/)? This order depends on which symbols are present in a way that's silly, hard to implement, and gains us very little.
    * ```encode.py```
        * implement ```error_correct_AI``` if needed?
        * add to ```validate``` if needed?
        * implement ```limit_to_AI_training_cards```?
        * Split composite text lines (i.e. "flying, first strike" -> "flying\first strike") and put the lines into canonical order? This would require starting training over from scratch, so likely not worth it.
    * update ```torch-rnn``` to handle ```rand_mtg_fields``` argument given new field sep, card sep, and mana formats from ```encode.py``` ?


# Environment Setup
Install NVidia CUDA toolkit version 11.8. (Trying newer versions may require manual customization of subtrees, especially torch-rnn which is no longer developed.)

### A1SD
* download this [custom model from civitai](https://civitai.com/models/16682/nov-mtg-art-v23) to ```A1SD/models/ldm/stable-diffusion-v1/```. Git does not support large files (several GB), so these files are not committed to the repo.
* set ```install_dir``` in ```webui.sh```
* update ```COMMANDLINE_ARGS``` in ```webui-user.sh``` based on your amount of ram, see [docs](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Command-Line-Arguments-and-Settings)
* launch ```bash webui.sh``` to finish setup
    * the first time it runs, it will download a bunch of dependancies (several GB)
    * it's ready once it launches the webserver (eg it prints ```Running on local URL:  http://127.0.0.1:7860```)
    <!-- * Optionally, if you plan to create your own embedding: Open that IP address in a browser -> ```Extensions``` tab -> ```Available``` sub tab -> install ```embedding-inspector``` -->
    * and you can then ```ctrl+c``` it to close the process for now

### llm
* ```cd llm```
* ```bash setup.sh```
    * might be able to unpin deepspeed, there was a [bug](https://github.com/huggingface/transformers/issues/24040) (and [this](https://github.com/microsoft/DeepSpeed/issues/3678)) in main branch when I installed it
* ```conda run -n llm python download-model.py timdettmers/guanaco-65b-merged``` (~160 GB)
    * May need to copy tokenizer configs from [here](https://huggingface.co/huggyllama/llama-65b) ([transformers RecursionError](https://github.com/huggingface/transformers/issues/22762))
* launch ```server.py``` to finish setup
    * the first time it runs, it will download a bunch of dependancies (several GB)
    * it's ready once it launches the webserver (eg it prints ```Running on local URL: ```)
    * and you can then ```ctrl+c``` it to close the process for now

### torch-rnn
* Setup torch dev environment. Conda doesn't handle lua / torch very well. Lua-torch is no longer maintained, and we can't use an old cuda installation on newer cards, so just install torch globally to ```~/torch``` and fiddle until it works. The order of these steps is critical. If you screw up, its often easier to ```rm -rf ~/torch``` and start over than try to recover.
* install ```libhdf5-dev```
    * add ```deb [trusted=yes check-valid-until=no] http://dk.archive.ubuntu.com/ubuntu/ trusty main universe``` to ```/etc/apt/sources.list```
    * ```sudo apt update```
    * ```sudo apt-get install libhdf5-dev==1.8.11*```
    * ```sudo apt-mark hold libhdf5-dev``` to pin version
* ```conda env create -f environment-python.yaml```. Use this enviropnment only for the preprocessing script
* install the [nvidia cuda toolkit](https://developer.nvidia.com/cuda-toolkit), version 11.8
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
    <!-- reference https://github.com/nagadomi/distro.git ~/torch --recursive -->

### main repo
* ```sudo apt install expect``` to get unbuffer command
* Install [miniconda](https://docs.conda.io/en/latest/miniconda.html)
* ```conda env create -f environment.yaml```
* download ```nltk``` language files
    * ```cd ~/nltk_data```
    * ```python -c "import nltk; nltk.download('punkt')"```
* Pretrained AIs are provided for names and main text, but you can optionally train your own (eg with updated data inputs). 
    * Build a dataset to train the AIs upon
        * Download ```AllPrintings.json``` from [mtgjson website](http://mtgjson.com/) to ```raw_data_sources/.```
        * optionally update ```raw_data_sources/names.yaml``` and ```raw_data_sources/flavor.yaml``` manually with additional training data
        * run ```bash rebuild_data_sources.sh |& tee log-data-build.txt``` in ```scripts/```
            * use printed ```Average chunk length``` for each AI to update constants in ```generate_cards.py``` -> ```LSTM_LEN_PER_MAIN_TEXT```, ```LSTM_LEN_PER_NAME```, and ```LSTM_LEN_PER_FLAVOR```
            * use printed ```Longest chunk length``` for each AI to set minimum ```-seq_length``` argument to ```train.lua```
            * use printed ```Total vocabulary size``` for each AI to set ```-wordvec_size``` argument to ```train.lua```?
        * The dataset format is considered an implementation detail, so for more information on the format see ```scripts/encode.py```
    * Train AIs with commands similar to these.
        * ```th train.lua -gpu 0 -input_h5 ../encoded_data_sources/names.h5 -input_json ../encoded_data_sources/names.json -checkpoint_name ../nns/names_3/checkpoint -rand_chunks_n_epochs 5 -checkpoint_n_epochs 100 -validate_n_epochs 10 -print_every 1 -num_layers 3 -rnn_sizes "200, 200, 200" -max_epochs 100000000 -batch_size 2000 -seq_length 150 -dropout 0.5 -learning_rate 0.02 -lr_decay_n_epochs 30 -lr_decay_factor 0.985 -wordvec_size 74```
        * ```th train.lua -gpu 0 -input_h5 ../encoded_data_sources/main_text.h5 -input_json ../encoded_data_sources/main_text.json -checkpoint_name ../nns/main_text_13/checkpoint -rand_chunks_n_epochs 1 -checkpoint_n_epochs 30 -validate_n_epochs 1 -print_every 1 -num_layers 4 -rnn_sizes "600, 600, 600, 600" -max_epochs 100000000 -batch_size 260 -seq_length 900 -dropout 0.5 -learning_rate 0.001 -lr_decay_n_epochs 10 -lr_decay_factor 0.99 -wordvec_size 122```
        * ```th train.lua -input_h5 ../encoded_data_sources/flavor.h5 -input_json ../encoded_data_sources/flavor.json -checkpoint_name ../nns/flavor_0/checkpoint -rand_chunks_n_epochs 1 -checkpoint_n_epochs 100 -validate_n_epochs 1 -print_every 1 -num_layers 3 -rnn_size 256 -max_epochs 100000000 -batch_size 200 -seq_length 500 -dropout 0.5 -learning_rate 0.002 -lr_decay_n_epochs 50 -lr_decay_factor 0.99```
        * ```CTRL+c``` to stop training when the AI is ready. Use ```scripts/plot_nn_loss.py``` to assess progress.
        * Check that the trained AIs work with ```th sample.lua -checkpoint ../nns/names_0/checkpoint_1001.000000.t7 -length 50```. The main generator will use a similar command to sample the AIs when generating cards.


<!--     * Create an embedding of mtg frames/borders for stable diffusion: download a small dataset of full card images -> delete (to black) the art portions manually, so we just have frames, text, symbols, etc. -> save to ```raw_data_sources/mtg_frame```
        * launch ```bash webui.sh``` from ```A1SD```, open the web UI (IP/port printed to console) in a browser, go to ```Train``` tab
        * ```Preprocess images``` sub-tab -> ```Source directory = ../raw_data_sources/mtg_frame```, ```Destination directory = ../encoded_data_sources/mtg_frame```, ```width, height = 512```, ```Existing Caption txt Action = ignore```, ```Split oversized images```, ```Split image threshold = 1```, ```Split image overlap ratio = 0.5``` -> ```Preprocess``` button. This will download several more GB, and then take several hours.
        * ```Create embedding``` tab -> ```Name = mtgframe```, ```Number of vectors per token = 30``` -> ```Create Embedding``` button
        * ```Train``` tab -> ```Embedding = mtgframe```, ```Batch size = 1```, ```Gradient accumulation steps = 1```, ```Embedding Learning rate = 0.005:1, 0.00475:580, 0.00451:1160, 0.00429:1740, 0.00407:2320, 0.00387:2900, 0.00368:3480, 0.00349:4060, 0.00332:4640, 0.00315:5220, 0.00299:5800, 0.00284:6380, 0.0027:6960, 0.00257:7540, 0.00244:8120, 0.00232:8700, 0.0022:9280, 0.00209:9860, 0.00199:10440, 0.00189:11020, 0.00179:11600, 0.0017:12180, 0.00162:12760, 0.00154:13340, 0.00146:13920, 0.00139:14500, 0.00132:15080, 0.00125:15660, 0.00119:16240, 0.00113:16820, 0.00107:17400, 0.00102:17980, 0.000969:18560, 0.00092:19140, 0.000874:19720, 0.00083:20300, 0.000789:20880, 0.000749:21460, 0.000712:22040, 0.000676:22620, 0.000643:23200, 0.00061:23780, 0.00058:24360, 0.000551:24940, 0.000523:25520, 0.000497:26100, 0.000472:26680, 0.000449:27260, 0.000426:27840, 0.000405:28420, 0.000385:29000, 0.000365:29580, 0.000347:30160, 0.00033:30740, 0.000313:31320, 0.000298:31900, 0.000283:32480, 0.000269:33060, 0.000255:33640, 0.000242:34220, 0.00023:34800, 0.000219:35380, 0.000208:35960, 0.000197:36540, 0.000188:37120, 0.000178:37700, 0.000169:38280, 0.000161:38860, 0.000153:39440, 0.000145:40020, 0.000138:40600, 0.000131:41180, 0.000124:41760, 0.000118:42340, 0.000112:42920, 0.000107:43500, 0.000101:44080, 9.63e-05:44660, 9.15e-05:45240, 8.69e-05:45820, 8.26e-05:46400, 7.84e-05:46980, 7.45e-05:47560, 7.08e-05:48140, 6.73e-05:48720, 6.39e-05:49300, 6.07e-05:49880, 5.77e-05:50460, 5.48e-05:51040, 5.2e-05:51620, 4.94e-05:52200, 4.7e-05:52780, 4.46e-05:53360, 4.24e-05:53940, 4.03e-05:54520, 3.83e-05:55100, 3.63e-05:55680, 3.45e-05:56260, 3.28e-05:56840, 3.12e-05:57420, 2.96e-05:58000, 2.81e-05:58580, 2.67e-05:59160, 2.54e-05:59740, 2.41e-05:60320, 2.29e-05:60900, 2.18e-05:61480, 2.07e-05:62060, 1.96e-05:62640, 1.87e-05:63220, 1.77e-05:63800, 1.68e-05:64380, 1.6e-05:64960, 1.52e-05:65540, 1.44e-05:66120, 1.37e-05:66700, 1.3e-05:67280, 1.24e-05:67860, 1.18e-05:68440, 1.12e-05:69020, 1.06e-05:69600, 1.01e-05:70180, 9.58e-06:70760, 9.1e-06:71340, 8.64e-06:71920, 8.21e-06:72500, 7.8e-06:73080, 7.41e-06:73660, 7.04e-06:74240, 6.69e-06:74820, 6.35e-06:75400, 6.04e-06:75980, 5.73e-06:76560, 5.45e-06:77140, 5.18e-06:77720, 4.92e-06:78300, 4.67e-06:78880, 4.44e-06:79460, 4.22e-06:80040, 4e-06:80620, 3.8e-06:81200, 3.61e-06:81780, 3.43e-06:82360, 3.26e-06:82940, 3.1e-06:83520, 2.94e-06:84100, 2.8e-06:84680, 2.66e-06:85260, 2.52e-06:85840, 2.4e-06:86420, 2.28e-06:87000, 2.16e-06:87580, 2.06e-06:88160, 1.95e-06:88740, 1.86e-06:89320, 1.76e-06:89900, 1.67e-06:90480, 1.59e-06:91060, 1.51e-06:91640, 1.44e-06:92220, 1.36e-06:92800, 1.3e-06:93380, 1.23e-06:93960, 1.17e-06:94540, 1.11e-06:95120, 1.06e-06:95700, 1e-06:96280, 9.52e-07:96860, 9.05e-07:97440, 8.6e-07:98020, 8.17e-07:98600, 7.76e-07:99180, 7.37e-07:99760```, ```Dataset directory = ../encoded_data_sources/mtg_frame```, ```Prompt template file = ../encoded_data_sources/frame_surrounds.txt```, ```Width, Height = 512```, ```Max steps = 100000```, ```Save an image... = 2* dataset size, and Save a copy... = dataset size```, uncheck ```Save images with embedding in PNG chunks``` -> ```Train Embedding``` button -->
<!--     * Create a Lora model for MTG art
        * Download ```unique-artwork-*.json``` from [scryfall](https://scryfall.com/docs/api/bulk-data) to ```raw_data_sources/unique-artwork.json```
        * run ```download_scryfall_art.py``` in ```scripts/```. This will acquire \~3GB of data, and take about 1.5 hours while respecting their rate limit.
            * scrub these images manually, deleting those insuitable for card art (card backs, placeholders, rules text, symbols, etc). A few images may need to be cropped instead. Due to size, I can't commit the reduced dataset to the git repo, but the vast majority of the images are fine, just a few clusters of placeholder images and what-not.
        * launch ```bash webui.sh``` from ```A1SD```, open the web UI (IP/port printed to console) in a browser, go to ```Train``` tab
            * ```Preprocess images``` sub-tab -> ```Source directory = ../raw_data_sources/mtg_art```, ```Destination directory = ../encoded_data_sources/mtg_art```, ```width, height = 512```, ```Existing Caption txt Action = copy```, check ```Split oversized images```, ```Split image threshold = 1```, ```Split image overlap ratio = 0.5``` -> ```Preprocess``` button. This will download several more GB, and then take several hours.
            * Go to the ```Extensions``` tab -> Install [```sd_dreambooth_extension```](https://github.com/d8ahazard/sd_dreambooth_extension.git) -> restart the web server entirely so it downloads new dependancies
            * Go to the ```Dreambooth``` tab
                * Under ```Settings``` sub-tab, check ```Use Lora```, and set parameters ```Epochs = 100, Pause After = 0, Save Frequency = 1, Save Previews = 1, Batch Size = 1, Gradient Accumulation = 1, Class Batch Size = 1, Gradient Checkpointing = False, Learning Rate Scheduler = constant_with_warmup, Learning Rate = 0.000002, Lora UNET Learning Rate = 0.0002, Lora Text Encoder Learning Rate = 0.0002, Learning Rate Warmup Steps = 0, Resolution = 512```, Uncheck ```Center Crop``` and ```Apply Horizontal Flip```, Set ```Sanity Sample Prompt = mss style Wall of the Geist```, set ```Sanity Sample Seed = 481992436```. Under Advanced sub-tab, uncheck ```Use 8bit Adam```, set ```Mixed Precision = no```, set ```Memory Attention = default```, check ```Cache Latents```, uncheck ```Pad Tokens```, uncheck ```Shuffle Tags```. Click ```Save and Test Webhook```. Select ```Save Settings``` button near the top of the dreambooth tab. Maybe need to click this twice as it throws an error the first time before it creates the settings file, and may need to select ```Save and Test Webhook``` again after this? I just ended up hitting ```Save Settings``` frequently, cause I wasn't sure exactly which configuation would be saved and which wouldn't.
                    * Note, higher batch sizes just don't seem to work. It always throws an error on tensor sizes not matching, despite setting it to a divisor of hte corpus per the [wiki](https://github.com/d8ahazard/sd_dreambooth_extension/wiki/Batch-Size).
                * Under ```Create``` sub-tab, set ```name = mss```, check ```512x model```, uncheck ```Create from Hub```, set ```Source Checkpoint = sd-v1-4.ckpt```, set ```Scheduler = euler```? Then select ```Create Model``` and wait for it to finish.
                    * name was selected from a [list of rare tokens used in stable diffusion](https://old.reddit.com/r/StableDiffusion/comments/zc65l4/rare_tokens_for_dreambooth_training_stable/). That token is used throughout as the prompt identifier for the trained style.
                * Under ```Concepts``` sub-tab, set ```Dataset Directory = ../encoded_data_sources/mtg_art```, leave empty ```Classification Dataset Directory```, clear ```Instance Token``` and ```Class Token```, set ```Instance Prompt = mss style [filewords]```, leave empty ```Class Prompt```, set ```Sample Image Prompt = mss style Wall of the Geist```, leave empty ```Classification Image Negative Prompt``` and ```Sample Prompt Template File```, ```Sample Negative Prompt = card frame, blurry, text, watermarks, logo, (bad_prompt:0.8), multiple arms, extra limbs, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, bad proportions, glitchy, bokeh```
                * Under ```Saving``` sub-tab, ```Custom Model Name = mss```, check ```Save Checkpoint to Subdirectory```, ```Generate a .ckpt file when saving during training```, ```Generate a .ckpt file when training completes```, ```Generate a .ckpt file when training is canceled```, ```Generate lora weights when saving during training```, ```Generate lora weights when training completes```, and ```Generate lora weights when training is canceled```
                * hit ```Train```
                    * Note only the ```Settings``` sub-tab is loaded when using the ```Load Settings``` button, so the changes to the other tabs must be completed each time the UI is reloaded.
                * see also, a bit of a guide on style training [here](https://github.com/d8ahazard/sd_dreambooth_extension/discussions/443) and some parameter explanation in the [readme](https://github.com/d8ahazard/sd_dreambooth_extension) -->

# Repo Data Structure
* ```raw_data_sources``` include user inputs for AI training data. These are processed into ```encoded_data_sources``` via ```rebuild_data_sources.sh```, which utilizes ```scripts/encode.py``` and ```torch-rnn```.
* ```nns``` contains trained text-based neural networks
* ```torch-rnn``` contains code for training and sampling the text neural networks
* ```A1SD``` contains image generating neural networks and associated code.
* ```llm``` contains text generating neural networks and associated code.
* ```scripts``` contains the main generator entry point ```generate_cards.py``` as well as intermediary and utility scripts
* ```outputs``` contains rendered card images, card sheets, full text and stats yaml files, and cached intermediate steps
* ```image_templates``` contains template images for rendering the generated cards


# Subtree List and their Customizations
### [torch-rnn](https://github.com/jcjohnson/torch-rnn), with some modifications inspired by [mtg-rnn](https://github.com/billzorn/mtg-rnn)
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

### [A1SD](https://github.com/AUTOMATIC1111/stable-diffusion-webui) (aka AUTOMATIC1111 webui for stable diffusion)
* customized install dir, API, and vram usage
* forced unbuffering to python call for reading server state when called as a subprocess

### [llm](https://github.com/oobabooga/text-generation-webui) (aka oobabooga webui for large language models)
* added ```setup.py```


# Util
* ```watch -n1 nvidia-smi``` to see GPU resource utilization
* [torch docs](https://github.com/torch/torch7/blob/master/doc/tensor.md)
* batch convert svg images to png ```find . -name "*.svg" | xargs inkscape --export-type=png --export-width=1000 --export-height=1000 --export-png-color-mode=RGBA_8 --batch-process```
* ```python plot_nn_loss.py --json_path nns/names_1/checkpoint_21.000000.json```
* after changing ```environment.yaml``` update the environment with ```conda deactivate && conda env remove --name mtg-ai-main && conda env create -f environment.yaml && conda activate mtg-ai-main```
* working with unicode in lua: http://lua-users.org/wiki/LuaUnicode
* each subtree has a remote under the same name as the directory
    * create remote: ```git remote add -f <name> <url>```
    * add subtree: ```git subtree add --prefix <dir> <remote> <branch> --squash```
    * pull subtree: ```git fetch <remote> <branch>``` and then ```git subtree pull --prefix <dir> <remote> <branch> --squash```
* Stable Diffusion prompt development tooling
    * [Lexica](https://lexica.art/) and [OpenArt](https://openart.ai/) provide generated images and their prompts
    * [img2prompt](https://replicate.com/methexis-inc/img2prompt) and [BLIP](https://huggingface.co/spaces/Salesforce/BLIP) predict the prompts for uploaded images
    * etc: see [reddit tooling catalog](https://old.reddit.com/r/StableDiffusion/comments/xcq819/dreamers_guide_to_getting_started_w_stable/)
<!-- * additional template images, fonts, etc at https://github.com/MrTeferi/cardconjurer and its forks-->

