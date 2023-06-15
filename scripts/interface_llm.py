import nltk
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
def start_server(verbosity, model, gpu_memory, cpu_memory, max_retries=10):
    # starts server and waits for it to be ready before returning

    global PROCESS
    if PROCESS is not None:
        raise RuntimeError(f'llm server should already be running?\n\tPID: {PROCESS.pid}\n\tpoll: {PROCESS.poll()}')

    if verbosity > 1:
        print('Starting llm server (slow)')

    PROCESS = subprocess.Popen(f'conda run'
                                    f' --no-capture-output'
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

        if PROCESS.poll() is not None:
            raise RuntimeError(f'llm server terminated unexpectedly\n\tPID: {PROCESS.pid}\n\tpoll: {PROCESS.poll()}\n{time.sleep(1) or ""}{"".join(PROCESS.stdout.readlines())}')
    else:
        raise RuntimeError(f'llm server startup timed-out\n\tPID: {PROCESS.pid}\n\tpoll: {PROCESS.poll()}\n{time.sleep(1) or ""}{"".join(PROCESS.stdout.readlines())}')

    assert server_up(verbosity)
    time.sleep(1)

    # check for a common runtime error (empty response) that only shows up when text is generated
    # note that this sample call should not cause recursion to this function
    try:
        # try generating a very short sequence. Length does not matter since the error shows up before any tokens are generated
        if verbosity > 2:
            print(f'Attempting llm test sample, at max_retries = {max_retries}')

        sample('banana', model, gpu_memory, cpu_memory, -1, verbosity, max_len=2)

        if verbosity > 2:
            print('Test sample succeeded, server started up successfully, yielding to sampler')

    except AssertionError as e:
        if verbosity > 2:
            print('Test sample threw AssertionError')

        if not re.search('Got empty response from llm', str(e)):
            raise
        elif max_retries <= 0:
            print('Exceeded max retries for llm server start')
            raise
        else:
            if verbosity > 1:
                print('llm server failed to sample, restarting it')
            if verbosity > 2:
                print(str(e))
            terminate_server(verbosity)
            start_server(verbosity, model, gpu_memory, cpu_memory, max_retries - 1)


def terminate_server(verbosity):
    global PROCESS

    if PROCESS is not None:
        if verbosity > 1:
            print('Terminating llm server')

        # cannot use Popen.terminate() or kill() because they will not kill further spawned processes, especially the process responsible for consuming vram
        os.killpg(os.getpgid(PROCESS.pid), signal.SIGTERM)
        PROCESS.communicate(timeout=60)  # clears pipe buffers, and waits for process to close

        PROCESS = None


def sample(prompt, model, gpu_memory, cpu_memory, seed, verbosity, max_len=75):
    # start web server if its not already up
    # Note this will not adjust the model (costly) if the server was started with a different model than currently requested
    if not server_up(verbosity):
        start_server(verbosity, model, gpu_memory, cpu_memory)

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
    }

    # decode the response
    response = requests.post(f'{ADDRESS}/api/v1/generate', json=payload)
    assert response.status_code == 200, f'llm returned error code {response.status_code}: {response.text}'

    response = response.json()
    generated_text = response['results'][0]['text']
    assert generated_text, (f'Got empty response from llm: {response}.'
                            f' This often coincides with the common runtime error where probability tensor contains invalid values,'
                            f' which is some kind of bug in the llm code or environment setup. '
                            f' In that case, just kill the server and start it again: might get it to work like 15% of the time.'
                            f'\n{time.sleep(1) or ""}{"".join(PROCESS.stdout.readlines())}')

    # clear pipe buffer, OS can block on this being full
    PROCESS.stdout.readlines()

    return generated_text


def trim_unfinished_sentences(s):
    # sample len is limited, so it can cut off in the middle of a sentence
    #   I'd rather trim those extra bits than try to finish them, since max len is due to high generatation time costs
    # can't quite use nltk tokenizer directly to determine if a trailing sentence is present
    #   because the function text_contains_sentbreak specifically ignores the last token
    #   And also because I want to preserve whitespace in sentence recombination
    #   So we will instantiate our own tokenizer, and implement our own sentbreak search
    # See nltk implementations here, which we largely copy until the last small modification
    #   https://www.nltk.org/_modules/nltk/tokenize.html#sent_tokenize
    #   https://www.nltk.org/_modules/nltk/tokenize/punkt.html#PunktSentenceTokenizer.tokenize
    #   https://www.nltk.org/_modules/nltk/tokenize/punkt.html#PunktSentenceTokenizer.sentences_from_text
    #   https://www.nltk.org/_modules/nltk/tokenize/punkt.html#PunktSentenceTokenizer.text_contains_sentbreak

    tokenizer = nltk.data.load(f"tokenizers/punkt/english.pickle")
    indices = list(tokenizer.span_tokenize(s))  # start/stop tuples for sentence boundaries

    # don't trim the text to nothing, even if the sentence doesn't terminate
    if len(indices) <= 1:
        return s

    # collect indices into s indicating the last and 2nd to last sentence boundaries
    trim_index = indices[-2][1]  # end of 2nd to last sentence, which is not equal to the next line
    last_sent_index = indices[-1][0]  # beginning of last sentence

    # check if last sentence terminates
    last_sent = s[last_sent_index:]
    annot = list(tokenizer._annotate_tokens(tokenizer._tokenize_words(last_sent)))
    last_token = annot[-1]
    
    if last_token.sentbreak:
        # last sentence terminates, do not modify the input
        return s

    else:
        # trailing sentence should be trimmed
        # preserving whitespace between sentences from the input string, in case its in haiku form or something
        return s[:trim_index]


def sample_flavor(card, model, gpu_memory, cpu_memory, cache_path, seed, verbosity):
    # handles file caching, prompting and sampling the llm based on card data, and processing the sampled data
    
    # remove cached file if it already exists
    if os.path.exists(cache_path):
        os.remove(cache_path)
        if verbosity > 2:
            print(f'Overwriting {cache_path}')
    else:
        if verbosity > 2:
            print(f'Caching to {cache_path}')

    # sample 
    prompt = (f'### Instruction:\n'
              f'Write short flavor text for an MTG card named "{card["name"]}" with type "{card["type"]}".\n\n'  # note two newlines
              f'### Response:\n'
              f'Flavor Text:\n'
              f'"')

    generated_text = sample(prompt, model, gpu_memory, cpu_memory, seed, verbosity)

    # trim response to earliest double quote, if any, not including the quote
    generated_text = re.sub('".*$', '', generated_text)

    generated_text = trim_unfinished_sentences(generated_text)

    # cache text
    f = open(cache_path, 'w')
    f.write(generated_text)
    f.close()

    return generated_text

