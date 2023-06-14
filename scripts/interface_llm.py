import os
import re
import requests
import signal
import subprocess
import sys
import time


# Constants
ADDRESS = 'http://127.0.0.1:5000'
PATH = '../llm'

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
        requests.get(f'{ADDRESS}/api/v1/model')
        if verbosity > 2:
            print('llm server is up')
        return True
    except requests.exceptions.ConnectionError:
        if verbosity > 2:
            print('llm server is not up')
        return False


PROCESS = None  # keep this around so the process can be killed on exit
def start_server(verbosity, model, gpu_memory, cpu_memory):
    # starts server and waits for it to be ready before returning

    global PROCESS
    if PROCESS is not None:
        raise RuntimeError(f'llm server should already be running?\n\tPID: {PROCESS.pid}\n\tpoll: {PROCESS.poll()}')

    if verbosity > 1:
        print('Starting llm server')

    PROCESS = subprocess.Popen(f'conda run'
                                    f' --live-stream'
                                    f' -n llm'
                                    f' deepspeed'
                                         f' --num_gpus=1'
                                         f' server.py'
                                              f' --deepspeed'
                                              f' --model {model}'
                                              f' --gpu-memory {gpu_memory}'
                                              f' --cpu-memory {cpu_memory}'
                                              f' --api',
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

    startup_timeout = 60 * 5  # seconds
    poll_frequency = 10  # Hz
    for i in range(startup_timeout * poll_frequency):
        time.sleep(1 / poll_frequency)
        line = PROCESS.stdout.readline()
        if re.search('Running on local URL', line):
            break
    else:
        raise RuntimeError(f'llm server startup timed-out\n\tPID: {PROCESS.pid}\n\tpoll: {PROCESS.poll()}')

    assert server_up(verbosity)


def terminate_server(verbosity):
    if PROCESS is not None:
        if verbosity > 1:
            print('Terminating llm server')

        # cannot use Popen.terminate() or kill() because they will not kill further spawned processes, especially the process responsible for consuming vram
        os.killpg(os.getpgid(PROCESS.pid), signal.SIGTERM)
        PROCESS.communicate(timeout=30)  # clears pipe buffers, and waits for process to close


def sample(prompt, model, gpu_memory, cpu_memory, max_len, cache_path, seed, verbosity):
    # start web server if its not already up
    # Note this will not adjust the model (costly) if the server was started with a different model than currently requested
    if not server_up(verbosity):
        start_server(verbosity, model, gpu_memory, cpu_memory)

    # remove cached file if it already exists
    if os.path.exists(cache_path):
        os.remove(cache_path)
        if verbosity > 2:
            print(f'Overwriting {cache_path}')
    else:
        if verbosity > 2:
            print(f'Caching to {cache_path}')

    # execute API call
    # see these addresses for API. I couldn't find proper docs.
    #   example usage: https://github.com/oobabooga/text-generation-webui/tree/main/extensions/api
    #   implementation: https://github.com/oobabooga/text-generation-webui/blob/main/extensions/api/blocking_api.py

    payload = {
        'prompt': prompt,
        'seed': seed,
        'max_new_tokens': max_len,
        'do_sample': True,
        'temperature': 0.7,
        'top_p': 0.9,

        # 'typical_p': 1,
        # 'epsilon_cutoff': 0,  # In units of 1e-4
        # 'eta_cutoff': 0,  # In units of 1e-4
        # 'tfs': 1,
        # 'top_a': 0,
        # 'repetition_penalty': 1.18,
        # 'top_k': 40,
        # 'min_length': 0,
        # 'no_repeat_ngram_size': 0,
        # 'num_beams': 1,
        # 'penalty_alpha': 0,
        # 'length_penalty': 1,
        # 'early_stopping': False,
        # 'mirostat_mode': 0,
        # 'mirostat_tau': 5,
        # 'mirostat_eta': 0.1,
        # 'add_bos_token': True,
        # 'truncation_length': 2048,
        # 'ban_eos_token': False,
        # 'skip_special_tokens': True,
        # 'stopping_strings': []
    }

    # decode the response
    response = requests.post(f'{ADDRESS}/api/v1/generate', json=payload)
    assert response.status_code == 200, f'llm returned error code {response.status_code}: {response.text}'

    response = response.json()
    generated_text = response['results'][0]['text']
    assert text, f'Got empty response from llm: {response.text}.'
                 f' This often coincides with the common runtime error where probability tensor contains invalid values,'
                 f' which is some kind of bug in the llm code or environment setup. '
                 f' In that case, just kill the server and start it again: might get it to work like 15% of the time.'
                 f'\n{time.sleep(1) or ""}{"".join(PROCESS.stdout.readlines())}'

    # clear pipe buffer, OS can block on this being full
    PROCESS.stdout.readlines()

    # cache text
    f = open(cache_path, 'w')
    f.write(generated_text)
    f.close()

    return generated_text

