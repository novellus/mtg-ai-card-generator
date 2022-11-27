import argparse, os, re
import cv2
import torch
import numpy as np
from random import randint
from omegaconf import OmegaConf
from PIL import Image
from tqdm import tqdm, trange
from imwatermark import WatermarkEncoder
from itertools import islice
from einops import rearrange
from torchvision.utils import make_grid
import time
from pytorch_lightning import seed_everything
from torch import autocast
from contextlib import contextmanager, nullcontext

from ldm.util import instantiate_from_config
from optimUtils import split_weighted_subprompts, logger
from transformers import logging
# from samplers import CompVisDenoiser
logging.set_verbosity_error()


# don't load safety model to save vram
# from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
# from transformers import AutoFeatureExtractor
# safety_model_id = "CompVis/stable-diffusion-safety-checker"
# safety_feature_extractor = AutoFeatureExtractor.from_pretrained(safety_model_id)
# safety_checker = StableDiffusionSafetyChecker.from_pretrained(safety_model_id)


def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())


def numpy_to_pil(images):
    """
    Convert a numpy image or a batch of images to a PIL image.
    """
    if images.ndim == 3:
        images = images[None, ...]
    images = (images * 255).round().astype("uint8")
    pil_images = [Image.fromarray(image) for image in images]

    return pil_images


def load_model_from_config(ckpt, verbose=False):
    print(f"Loading model from {ckpt}")
    pl_sd = torch.load(ckpt, map_location="cpu")
    if "global_step" in pl_sd:
        print(f"Global Step: {pl_sd['global_step']}")
    sd = pl_sd["state_dict"]
    return sd


def put_watermark(img, wm_encoder=None):
    if wm_encoder is not None:
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        img = wm_encoder.encode(img, 'dwtDct')
        img = Image.fromarray(img[:, :, ::-1])
    return img


def load_replacement(x):
    try:
        hwc = x.shape
        y = Image.open("assets/rick.jpeg").convert("RGB").resize((hwc[1], hwc[0]))
        y = (np.array(y)/255.0).astype(x.dtype)
        assert y.shape == x.shape
        return y
    except Exception:
        return x


def check_safety(x_image):
    safety_checker_input = safety_feature_extractor(numpy_to_pil(x_image), return_tensors="pt")
    x_checked_image, has_nsfw_concept = safety_checker(images=x_image, clip_input=safety_checker_input.pixel_values)
    assert x_checked_image.shape[0] == len(has_nsfw_concept)
    for i in range(len(has_nsfw_concept)):
        if has_nsfw_concept[i]:
            x_checked_image[i] = load_replacement(x_checked_image[i])
    return x_checked_image, has_nsfw_concept


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--prompt",
        type=str,
        nargs="?",
        default="a painting of a virus monster playing guitar",
        help="the prompt to render"
    )
    parser.add_argument(
        "--outdir",
        type=str,
        nargs="?",
        help="dir to write results to",
        default="outputs/txt2img-samples"
    )
    parser.add_argument(
        "--out_filename",
        type=str,
        nargs="?",
        help=r"defaults to '<folder sequence int>_<seed>'. Invalid to specify if number of output files is > 1",
        default=None
    )
    parser.add_argument(
        "--ddim_steps",
        type=int,
        default=50,
        help="number of ddim sampling steps",
    )
    parser.add_argument(
        "--fixed_code",
        action='store_true',
        help="if enabled, uses the same starting code across samples ",
    )
    parser.add_argument(
        "--ddim_eta",
        type=float,
        default=0.0,
        help="ddim eta (eta=0.0 corresponds to deterministic sampling",
    )
    parser.add_argument(
        "--n_iter",
        type=int,
        default=1,
        help="sample this often",
    )
    parser.add_argument(
        "--H",
        type=int,
        default=512,
        help="image height, in pixel space",
    )
    parser.add_argument(
        "--W",
        type=int,
        default=512,
        help="image width, in pixel space",
    )
    parser.add_argument(
        "--C",
        type=int,
        default=4,
        help="latent channels",
    )
    parser.add_argument(
        "--f",
        type=int,
        default=8,
        help="downsampling factor",
    )
    parser.add_argument(
        "--n_samples",
        type=int,
        default=3,
        help="how many samples to produce for each given prompt. A.k.a. batch size",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=7.5,
        help="unconditional guidance scale: eps = eps(x, empty) + scale * (eps(x, cond) - eps(x, empty))",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="specify GPU (cuda/cuda:0/cuda:1/...)",
    )
    parser.add_argument(
        "--from-file",
        type=str,
        help="if specified, load prompts from this file",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="optimizedSD/v1-inference.yaml",
        help="path to config which constructs model",
    )
    parser.add_argument(
        "--ckpt",
        type=str,
        default='models/ldm/stable-diffusion-v1/model.ckpt',
        help="path to checkpoint of model",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="the seed (for reproducible sampling)",
    )
    parser.add_argument(
        "--unet_bs",
        type=int,
        default=1,
        help="Slightly reduces inference time at the expense of high VRAM (value > 1 not recommended )",
    )
    parser.add_argument(
        "--turbo",
        action="store_true",
        help="Reduces inference time on the expense of 1GB VRAM",
    )
    parser.add_argument(
        "--force_no_arg_weighting",
        action="store_true",
        help="skips arg weighting even if prompt is formatted for it",
    )
    parser.add_argument(
        "--precision", 
        type=str,
        help="evaluate at this precision",
        choices=["full", "autocast"],
        default="autocast"
    )
    parser.add_argument(
        "--format",
        type=str,
        help="output image format",
        choices=["jpg", "png"],
        default="png",
    )
    parser.add_argument(
        "--sampler",
        type=str,
        help="sampler",
        choices=["ddim", "plms","heun", "euler", "euler_a", "dpm2", "dpm2_a", "lms"],
        default="plms",
    )
    opt = parser.parse_args()

    tic = time.time()
    os.makedirs(opt.outdir, exist_ok=True)
    outpath = opt.outdir

    assert opt.out_filename is None or (opt.n_samples == 1 and opt.n_iter == 1)

    print("Creating invisible watermark encoder (see https://github.com/ShieldMnt/invisible-watermark)...")
    wm = "StableDiffusionV1"
    wm_encoder = WatermarkEncoder()
    wm_encoder.set_watermark('bytes', wm.encode('utf-8'))

    if opt.seed == None:
        opt.seed = randint(0, 1000000)
    seed_everything(opt.seed)

    # Logging
    logger(vars(opt), log_csv = "logs/txt2img_logs.csv")

    sd = load_model_from_config(f"{opt.ckpt}")
    li, lo = [], []
    for key, value in sd.items():
        sp = key.split(".")
        if (sp[0]) == "model":
            if "input_blocks" in sp:
                li.append(key)
            elif "middle_block" in sp:
                li.append(key)
            elif "time_embed" in sp:
                li.append(key)
            else:
                lo.append(key)
    for key in li:
        sd["model1." + key[6:]] = sd.pop(key)
    for key in lo:
        sd["model2." + key[6:]] = sd.pop(key)

    config = OmegaConf.load(f"{opt.config}")

    model = instantiate_from_config(config.modelUNet)
    _, _ = model.load_state_dict(sd, strict=False)
    model.eval()
    model.unet_bs = opt.unet_bs
    model.cdevice = opt.device
    model.turbo = opt.turbo

    modelCS = instantiate_from_config(config.modelCondStage)
    _, _ = modelCS.load_state_dict(sd, strict=False)
    modelCS.eval()
    modelCS.cond_stage_model.device = opt.device

    modelFS = instantiate_from_config(config.modelFirstStage)
    _, _ = modelFS.load_state_dict(sd, strict=False)
    modelFS.eval()
    del sd

    if opt.device != "cpu" and opt.precision == "autocast":
        model.half()
        modelCS.half()

    start_code = None
    if opt.fixed_code:
        start_code = torch.randn([opt.n_samples, opt.C, opt.H // opt.f, opt.W // opt.f], device=opt.device)


    batch_size = opt.n_samples
    if not opt.from_file:
        assert opt.prompt is not None
        prompt = opt.prompt
        print(f"Using prompt: {prompt}")
        data = [batch_size * [prompt]]

    else:
        print(f"reading prompts from {opt.from_file}")
        with open(opt.from_file, "r") as f:
            text = f.read()
            print(f"Using prompt: {text.strip()}")
            data = text.splitlines()
            data = batch_size * list(data)
            data = list(chunk(sorted(data), batch_size))


    if opt.precision == "autocast" and opt.device != "cpu":
        precision_scope = autocast
    else:
        precision_scope = nullcontext

    seeds = ""
    with torch.no_grad():

        all_samples = list()
        for n in trange(opt.n_iter, desc="Sampling"):
            for prompts in tqdm(data, desc="data"):

                os.makedirs(outpath, exist_ok=True)
                base_count = len(os.listdir(outpath))

                with precision_scope("cuda"):
                    modelCS.to(opt.device)

                    if isinstance(prompts, tuple):
                        prompts = list(prompts)

                    # # '#' split negative prompts
                    # split_prompt = prompts[0].split('#')
                    # pos_prompt = split_prompt[0]
                    # if len(split_prompt) > 1:
                    #     neg_prompt = split_prompt[1]
                    #     uc = modelCS.get_learned_conditioning(batch_size * [neg_prompt])
                    # else:
                    #     uc = modelCS.get_learned_conditioning(batch_size * [""])
                    # c = modelCS.get_learned_conditioning(pos_prompt)

                    # # classic negative prompts
                    # subprompts, weights, neg_subprompts, neg_weights = split_weighted_subprompts(prompts[0])
                    # uc = None
                    # if opt.scale != 1.0:
                    #     uc = modelCS.get_learned_conditioning(batch_size * [""])  # just for shape initialization...
                    # if len(neg_subprompts) >= 1:
                    #     uc = torch.zeros_like(uc)
                    #     totalWeight = sum(neg_weights)
                    #     # normalize each "sub prompt" and add it
                    #     for i in range(len(neg_subprompts)):
                    #         weight = neg_weights[i]
                    #         weight = weight / totalWeight
                    #         uc = torch.add(uc, modelCS.get_learned_conditioning(neg_subprompts[i]), alpha=weight)
                    # if len(subprompts) >= 1:
                    #     c = torch.zeros_like(uc)
                    #     totalWeight = sum(weights)
                    #     # normalize each "sub prompt" and add it
                    #     for i in range(len(subprompts)):
                    #         weight = weights[i]
                    #         weight = weight / totalWeight
                    #         c = torch.add(c, modelCS.get_learned_conditioning(subprompts[i]), alpha=weight)
                    # else:
                    #     c = modelCS.get_learned_conditioning(prompts)

                    # intentionally broken negative prompts
                    subprompts, weights, neg_subprompts, neg_weights = split_weighted_subprompts(prompts[0])
                    uc = modelCS.get_learned_conditioning(batch_size * [""])
                    c = torch.zeros_like(uc)
                    totalWeight = sum(weights) - sum(neg_weights)
                    # normalize each "sub prompt" and add it
                    for i in range(len(subprompts)):
                        weight = weights[i]
                        weight = weight / totalWeight
                        c = torch.add(c, modelCS.get_learned_conditioning(subprompts[i]), alpha=weight)
                    for i in range(len(neg_subprompts)):
                        weight = -neg_weights[i]
                        weight = weight / totalWeight
                        c = torch.add(c, modelCS.get_learned_conditioning(neg_subprompts[i]), alpha=weight)

                    shape = [opt.n_samples, opt.C, opt.H // opt.f, opt.W // opt.f]

                    if opt.device != "cpu":
                        mem = torch.cuda.memory_allocated() / 1e6
                        modelCS.to("cpu")
                        while torch.cuda.memory_allocated() / 1e6 >= mem:
                            time.sleep(1)

                    samples_ddim = model.sample(
                        S=opt.ddim_steps,
                        conditioning=c,
                        seed=opt.seed,
                        shape=shape,
                        verbose=False,
                        unconditional_guidance_scale=opt.scale,
                        unconditional_conditioning=uc,
                        eta=opt.ddim_eta,
                        x_T=start_code,
                        sampler = opt.sampler,
                    )

                    modelFS.to(opt.device)

                    print(samples_ddim.shape)
                    print("saving images")
                    for i in range(batch_size):

                        x_samples_ddim = modelFS.decode_first_stage(samples_ddim[i].unsqueeze(0))
                        x_sample = torch.clamp((x_samples_ddim + 1.0) / 2.0, min=0.0, max=1.0)
                        x_sample = 255.0 * rearrange(x_sample[0].cpu().numpy(), "c h w -> h w c")

                        img = Image.fromarray(x_sample.astype(np.uint8))
                        if img.size[0] >= 256 and img.size[1] >= 256:
                            img = put_watermark(img, wm_encoder)
                        else:
                            print('Skipping watermarker, image too small. Dissemination of unwatermarked AI images may be considered unethical, and hinder future AI development.')
                        out_filename = opt.out_filename or f'{base_count:05}_{opt.seed}.{opt.format}'
                        img.save(os.path.join(outpath, out_filename))

                        seeds += str(opt.seed) + ","
                        opt.seed += 1
                        base_count += 1

                    if opt.device != "cpu":
                        mem = torch.cuda.memory_allocated() / 1e6
                        modelFS.to("cpu")
                        while torch.cuda.memory_allocated() / 1e6 >= mem:
                            time.sleep(1)
                    del samples_ddim
                    print("memory_final = ", torch.cuda.memory_allocated() / 1e6)

    toc = time.time()

    time_taken = (toc - tic) / 60.0

    print(
        (
            "Samples finished in {0:.2f} minutes and exported to "
            + outpath
            + "\n Seeds used = "
            + seeds[:-1]
        ).format(time_taken)
    )


if __name__ == "__main__":
    main()
