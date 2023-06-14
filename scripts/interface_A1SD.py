import base64
import io
import os
import re
import requests
import signal
import subprocess
import sys

from PIL import Image
from PIL import PngImagePlugin


# Constants
ADDRESS = 'http://127.0.0.1:7860'
PATH = '../A1SD'


def handle_sigint(signum, frame):
    # gracefull kill the server before exiting
    terminate_server(float('inf'))  # use infinite verbosity, since user ctrl+c'd
    sys.exit(0)
signal.signal(signal.SIGINT, handle_sigint)


def server_up(verbosity):
    # make an arbitrary API call to check if the server is up
    # we make this check instead of checking PROCESS object incase
    #   the server has failed, started with incorrect arguments, code error, server was started outside of this program, etc

    try:
        requests.get(f'{ADDRESS}/sdapi/v1/embeddings')
        if verbosity > 2:
            print('A1SD server is up')
        return True
    except requests.exceptions.ConnectionError:
        if verbosity > 2:
            print('A1SD server is not up')
        return False


PROCESS = None  # keep this around so the process can be killed on exit
def start_server(verbosity, model):
    # starts server and waits for it to be ready before returning

    global PROCESS
    if PROCESS is not None:
        raise RuntimeError(f'A1SD server should already be running?\n\tPID: {PROCESS.pid}\n\tpoll: {PROCESS.poll()}')

    if verbosity > 1:
        print('Starting A1SD server')

    PROCESS = subprocess.Popen('bash webui.sh',
                                shell=True,
                                bufsize=1,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                encoding='utf-8',
                                start_new_session=True,  # enables killing all spawned processes as a group
                                cwd=PATH)

    # wait for the server to startup to a ready state
    #   check for server to print its ready state to console
    # check server response using a non-blocking-read workaround
    #   this would be much easier if there was a supported simple interface to communicate with ongoing processes
    #   such as that implemented by threading - use a pipe, poll the pipe for data, read pipe data
    # however, the subprocess module doesn't provide anything so nice for ongoing processes
    #   docs suggest using Popen.communicate, but this doesn't support our use case since it waits for the process to finish, or raises a TimeoutExpired exception
    #   blindly calling Popen.stdout.read() or .readline() will cause hangs, since these both wait for a certain code to be written to stream before returning
    # so instead, we're gonna modify the file stream provided by Popen to implement a non-blocking read mechanism
    #   this causes the read() calls to always return, or throw an unhelpful TypeError if the stream is empty
    #   while readline() will just return an empty string when the stream is empty
    #   empty stream behavior plus line buffering makes readline the obvious preference here
    # Finally, the stream has no way to tell if it has data, so just read one line at a time at fixed frequency
    os.set_blocking(PROCESS.stdout.fileno(), False)

    startup_timeout = 60  # seconds
    poll_frequency = 10  # Hz
    for i in range(startup_timeout * poll_frequency):
        time.sleep(1 / poll_frequency)
        line = PROCESS.stdout.readline()
        if re.search('Running on local URL', line):
            break
    else:
        raise RuntimeError(f'A1SD server startup timed-out\n\tPID: {PROCESS.pid}\n\tpoll: {PROCESS.poll()}')

    assert server_up(verbosity)

    # Configure server
    payload = {'sd_model_checkpoint': model,
               'add_model_name_to_info': True,
               'face_restoration_model': 'GFPGAN',
              }
    response = requests.post(f'{ADDRESS}/sdapi/v1/options', json=payload)
    assert response.status_code == 200, response


def terminate_server(verbosity):
    if PROCESS is not None:
        if verbosity > 1:
            print('Terminating A1SD server')

        # cannot use Popen.terminate() or kill() because they will not kill further spawned processes, especially the process responsible for consuming vram
        os.killpg(os.getpgid(PROCESS.pid), signal.SIGTERM)
        PROCESS.communicate(timeout=10)  # clears pipe buffers, and waits for process to close

        PROCESS = None


def sample_txt2img(card, model, cache_path, seed, verbosity, hr_upscale=None):
    # start web server if its not already up
    # Note this will not adjust the model (costly) if the server was started with a different model than currently requested
    if not server_up(verbosity):
        start_server(verbosity, model)

    # remove cached file if it already exists
    if os.path.exists(cache_path):
        os.remove(cache_path)
        if verbosity > 2:
            print(f'Overwriting image file at {cache_path}')
    else:
        if verbosity > 2:
            print(f'Caching image file to {cache_path}')

    # execute txt2img
    # see f'{ADDRESS}/docs' for API description
    #   its outdated, and not all the listed APIs work, but still the best reference I have

    payload = {
        'prompt': f"{card['name']}, {card['type']}, high fantasy",

        # try to dissuade the AI from generating images of MTG cards, which adds confusing and undesired text/symbols/frame elements
        #   There's probably several better ways to approach this? Also these negative embeddings don't work very well, so just don't even use them...
        #   the mtgframe* keywords are embeddings, see https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#textual-inversion
        # 'negative_prompt': 'mtgframe5, mtgframe6, mtgframe7, mtgframe8, mtgframe10, mtgframe11, blurry, text',
        # 'negative_prompt': 'blurry, text, watermarks, logo, out of frame, extra fingers, mutated hands, monochrome, poorly drawn hands, poorly drawn face, mutation, deformed, ugly, bad anatomy, bad proportions, extra arms, extra limbs, cloned face, glitchy, bokeh',
        # With A/B testing, performance of the AI seems to be maximized when negative prompt is not used

        'steps': 20,
        'batch_size': 1,
        'n_iter': 1,
        'width': 512,
        'height': 512,
        'sampler_index': 'Euler a',  # also available: 'sampler_name'... ?
        'seed': seed,
        # 'restore_faces': True,
    }

    if hr_upscale is not None:
        # render the image orignally at 512x512 since the AI artifacts heavily at any other resolution
        # then use another AI to upscale to 1024x1024
        assert hr_upscale > 1, f'invalid hr_upscale {hr_upscale}, must be > 1'
        payload.update({
            'enable_hr': True,
            'hr_scale': hr_upscale,  # eg 2, see argparser
            'hr_upscaler': 'ESRGAN_4x',
            'denoising_strength': 0.2,  # empirical, subjective, heavily affects quality. High values introduce artifacts
            'hr_second_pass_steps': 20,
        })

    # decode the response
    #   we asked a batch processor for a single sample
    #   image data is base64 ascii-encoded
    response = requests.post(f'{ADDRESS}/sdapi/v1/txt2img', json=payload)
    assert response.status_code != 500, f'500 status code: frequently means out of memory error\n{time.sleep(1) or ""}{"".join(PROCESS.stdout.readlines())}'

    response = response.json()
    image_data = response['images'][0]
    im = Image.open(io.BytesIO(base64.b64decode(image_data)))

    # clear pipe buffer, OS can block on this being full
    PROCESS.stdout.readlines()

    # request png info blob from the server
    #   which gives us enough information about the generated image to regenerate it
    #   ie: all txt2img input parameters, including those which have default values and are not specified here
    # This info blob will be saved as part of the image data
    #   and is in a format which the AUTOMATIC1111 web server understands, so we're not gonna add random whatevers to it
    response = requests.post(f'{ADDRESS}/sdapi/v1/png-info', json={"image": "data:image/png;base64," + image_data})
    png_info = response.json()['info']

    # cache image
    encoded_info = PngImagePlugin.PngInfo()
    encoded_info.add_text("parameters", png_info)  # 'parameters' key is looked for by AUTOMATIC1111 web server
    im.save(cache_path, pnginfo=encoded_info)

    return im, png_info

