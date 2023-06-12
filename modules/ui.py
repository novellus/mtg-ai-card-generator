from pathlib import Path

import gradio as gr
import torch

from modules import shared

with open(Path(__file__).resolve().parent / '../css/main.css', 'r') as f:
    css = f.read()
with open(Path(__file__).resolve().parent / '../css/chat.css', 'r') as f:
    chat_css = f.read()
with open(Path(__file__).resolve().parent / '../css/main.js', 'r') as f:
    main_js = f.read()
with open(Path(__file__).resolve().parent / '../css/chat.js', 'r') as f:
    chat_js = f.read()

refresh_symbol = '\U0001f504'  # 🔄
delete_symbol = '🗑️'
save_symbol = '💾'

theme = gr.themes.Default(
    font=['Helvetica', 'ui-sans-serif', 'system-ui', 'sans-serif'],
    font_mono=['IBM Plex Mono', 'ui-monospace', 'Consolas', 'monospace'],
).set(
    border_color_primary='#c5c5d2',
    button_large_padding='6px 12px',
    body_text_color_subdued='#484848',
    background_fill_secondary='#eaeaea'
)


def list_model_elements():
    elements = ['cpu_memory', 'auto_devices', 'disk', 'cpu', 'bf16', 'load_in_8bit', 'trust_remote_code', 'load_in_4bit', 'compute_dtype', 'quant_type', 'use_double_quant', 'gptq_for_llama', 'wbits', 'groupsize', 'model_type', 'pre_layer', 'triton', 'desc_act', 'threads', 'n_batch', 'no_mmap', 'mlock', 'n_gpu_layers', 'n_ctx', 'llama_cpp_seed']
    for i in range(torch.cuda.device_count()):
        elements.append(f'gpu_memory_{i}')

    return elements


def list_interface_input_elements(chat=False):
    elements = ['max_new_tokens', 'seed', 'temperature', 'top_p', 'top_k', 'typical_p', 'epsilon_cutoff', 'eta_cutoff', 'repetition_penalty', 'encoder_repetition_penalty', 'no_repeat_ngram_size', 'min_length', 'do_sample', 'penalty_alpha', 'num_beams', 'length_penalty', 'early_stopping', 'mirostat_mode', 'mirostat_tau', 'mirostat_eta', 'add_bos_token', 'ban_eos_token', 'truncation_length', 'custom_stopping_strings', 'skip_special_tokens', 'preset_menu', 'stream', 'tfs', 'top_a']
    if chat:
        elements += ['name1', 'name2', 'greeting', 'context', 'chat_prompt_size', 'chat_generation_attempts', 'stop_at_newline', 'mode', 'instruction_template', 'character_menu', 'name1_instruct', 'name2_instruct', 'context_instruct', 'turn_template', 'chat_style', 'chat-instruct_command']

    elements += list_model_elements()
    return elements


def gather_interface_values(*args):
    output = {}
    for i, element in enumerate(shared.input_elements):
        output[element] = args[i]

    shared.persistent_interface_state = output
    return output


def apply_interface_values(state, use_persistent=False):
    if use_persistent:
        state = shared.persistent_interface_state

    elements = list_interface_input_elements(chat=shared.is_chat())
    if len(state) == 0:
        return [gr.update() for k in elements]  # Dummy, do nothing
    else:
        return [state[k] if k in state else gr.update() for k in elements]


class ToolButton(gr.Button, gr.components.FormComponent):
    """Small button with single emoji as text, fits inside gradio forms"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_block_name(self):
        return "button"


def create_refresh_button(refresh_component, refresh_method, refreshed_args, elem_class):
    def refresh():
        refresh_method()
        args = refreshed_args() if callable(refreshed_args) else refreshed_args

        for k, v in args.items():
            setattr(refresh_component, k, v)

        return gr.update(**(args or {}))

    refresh_button = ToolButton(value=refresh_symbol, elem_classes=elem_class)
    refresh_button.click(
        fn=refresh,
        inputs=[],
        outputs=[refresh_component]
    )
    return refresh_button


def create_delete_button(**kwargs):
    return ToolButton(value=delete_symbol, **kwargs)


def create_save_button(**kwargs):
    return ToolButton(value=save_symbol, **kwargs)
