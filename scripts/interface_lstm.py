import math
import os
import shlex
import subprocess
import traceback


# Constants
PATH_TORCH_RNN = '../torch-rnn'

# average lengths, for initial LSTM sample length target
LEN_PER_MAIN_TEXT = 172  # average and empirical, change if the dataset changes (eg rebuild_data_sources.sh)
LEN_PER_NAME =      16   # average and empirical, change if the dataset changes (eg rebuild_data_sources.sh)
LEN_PER_FLAVOR =    105  # average and empirical, change if the dataset changes (eg rebuild_data_sources.sh)


# mana_cost_to_human_readable = {'B': 'black',
#                                'C': 'colorless_only',
#                                'E': 'energy',
#                                'G': 'green',
#                                'P': 'phyrexian',
#                                'R': 'red',
#                                'S': 'snow',
#                                'U': 'blue',
#                                'W': 'white',
#                                'X': 'X',
#                                # '\d': 'colorless',  # handled programatically
#                               }



def sample(nn_path, seed, approx_length_per_chunk, num_chunks, delimiter='\n', parser=None, initial_length_margin=1.05, trimmed_delimiters=2, deduplicate=True, max_resamples=3, length_growth=5, whisper_text=None, whisper_every_newline=1, verbosity=0, gpu=0):
    # samples from nn at nn_path with seed
    #   whispers whisper_text if specified, at interval whisper_every_newline
    # initially samples a length of characters targeting the number of chunks with margin
    # chunks on delimiter
    # trims trimmed_delimiters chunks from both beginning and end of stream
    # optionally deduplicates chunks
    # optionally parses chunks with given function
    #   if parser raises an error, the chunk is discarded
    # checks for atleast num_chunks remaining
    #   resamples at geometrically higher lengths (*length_growth) if criterion not met
    #   raises error if max_resamples exceeded
    # trims to num_chunks
    # returns list of chunks, or the returns the only chunk directly if num_chunks == 1.

    # set total sample length, including trimmed portion
    length = approx_length_per_chunk * (num_chunks + 2 * trimmed_delimiters) * initial_length_margin
    length = math.ceil(length)

    # sample nn
    for _ in range(max_resamples):
        cmd = ( 'th sample.lua'
               f' -checkpoint "{nn_path}"'
               f' -length {length}'
               f' -seed {seed}'
               f' -gpu {gpu}'
              )
        if whisper_text is not None:
            cmd += (f' -whisper_text {shlex.quote(whisper_text)}'
                    f' -whisper_every_newline {whisper_every_newline}'
                    f' -start_text {shlex.quote(whisper_text)}'
                   )

        try:
            p = subprocess.run(cmd,
                               shell=True,
                               capture_output=True,
                               check=True,
                               cwd=os.path.join(os.getcwd(), PATH_TORCH_RNN))
        except Exception as e:
            print('LSTM sampler threw an error')
            print(cmd)
            if e.stdout: print(e.stdout.decode('utf-8'))
            if e.stderr: print(e.stderr.decode('utf-8'))
            raise
        sampled_text = p.stdout.decode('utf-8')

        # delimit and trim
        chunks = sampled_text.split(delimiter)

        if trimmed_delimiters > 0:
            chunks = chunks[trimmed_delimiters : -trimmed_delimiters]

        # trim leading / trailing whitepsace
        chunks = [x.strip() for x in chunks]

        # deduplicate, but preserve order from the original input, for output stability over many runs
        if deduplicate:
            chunks = sorted(set(chunks), key=lambda x: chunks.index(x))

        if parser is not None:
            new_chunks = []
            for chunk in chunks:
                try:
                    new_chunk = parser(chunk)
                    new_chunks.append(new_chunk)
                except Exception as e:
                    if verbosity > 2:
                        print('Exception in LSTM parser')
                        print(f'\tchunk = "{chunk}"')
                        tb = traceback.format_exc()
                        tb = tb.strip()
                        tb = '\t' + '\n\t'.join(tb.split('\n'))
                        print(tb)
            chunks = new_chunks

        # check criterion
        if len(chunks) >= num_chunks:
            # trim to target number
            chunks = chunks[:num_chunks]

            # return either a list of many, or only a single item
            if num_chunks == 1:
                return chunks[0]
            else:
                return chunks

        else:
            if verbosity > 2:
                print(f'LSTM did not return enough chunks, looking for {num_chunks} but only got {len(chunks)}')
                print(f'\tcmd = "{cmd}"')
                print(f'\tchunks = "{chunks}"')

            # try again with a longer sample
            length *= length_growth

    raise ValueError(f'LSTM {nn_path} sample did not meet delimiter criterion at {length/length_growth} length, exceeded {max_resamples} resamples')

