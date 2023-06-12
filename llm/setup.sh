set -e

## install
conda remove -y -n llm --all
conda create -y -n llm python=3.10.9
conda run -n llm pip install --no-input torch torchvision torchaudio
conda run -n llm pip install --no-input -r requirements.txt
conda run -n llm pip install --no-input deepspeed==0.9.2
