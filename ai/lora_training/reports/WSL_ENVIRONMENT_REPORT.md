# WSL Environment Report

Date/time: 2026-04-28 14:08:17 +10:00

## Scope

Worker 003 created and verified the clean WSL conda environment for the ClearRead Llama-3.1-8B-Instruct SFT + QLoRA path.

No model training was run. No source datasets, approved split files, teammate exports, old WSL reference env, or old WSL reference project were modified.

## Docs Consulted

- Unsloth pip/uv install docs: https://unsloth.ai/docs/get-started/install/pip-install
- Unsloth fine-tuning guide: https://unsloth.ai/docs/get-started/fine-tuning-llms-guide
- Hugging Face TRL SFTTrainer docs: https://huggingface.co/docs/trl/sft_trainer
- PyTorch local install docs: https://pytorch.org/get-started/locally/

## WSL And Conda

- WSL distro: Ubuntu
- WSL version: 2
- Ubuntu release: 24.04.4 LTS, noble
- Kernel: 6.6.87.2-microsoft-standard-WSL2
- Conda path: `<conda-root>/bin/conda`
- Conda version: 26.1.1
- Environment name: `clearread-llama-lora`
- Environment path: `<conda-env-path>/clearread-llama-lora`
- Python executable: `<conda-env-path>/clearread-llama-lora/bin/python`
- Python version: 3.11.15

## Install Commands Used

```bash
source <conda-root>/etc/profile.d/conda.sh
conda create -y -n clearread-llama-lora python=3.11 pip
conda activate clearread-llama-lora
python -m pip install --upgrade pip setuptools wheel packaging ninja cmake
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
python -m pip install unsloth huggingface_hub safetensors sentencepiece protobuf
```

Notes:

- The initial PyTorch install used the CUDA 12.6 wheel index.
- The subsequent official simple `pip install unsloth` route resolved the stack to `torch 2.10.0+cu128`, `torchvision 0.25.0`, and CUDA 12.8 runtime packages.
- This resolved stack was kept because CUDA runtime verification passed on the local RTX 4070 Ti SUPER.

## GPU And CUDA Verification

WSL GPU query:

- GPU: NVIDIA GeForce RTX 4070 Ti SUPER
- VRAM: 16376 MiB from `nvidia-smi`; 16375.5 MiB from PyTorch properties
- Driver: 560.94

PyTorch verification inside `clearread-llama-lora`:

- `torch.__version__`: 2.10.0+cu128
- `torch.version.cuda`: 12.8
- `torch.cuda.is_available()`: true
- CUDA device count: 1
- GPU capability: 8.9
- CUDA tensor test: passed
- BF16 support: true

## Package Versions

| Package | Version |
|---|---:|
| torch | 2.10.0 |
| transformers | 5.5.0 |
| datasets | 4.3.0 |
| accelerate | 1.13.0 |
| peft | 0.19.1 |
| trl | 0.24.0 |
| bitsandbytes | 0.49.2 |
| unsloth | 2026.4.8 |
| huggingface_hub | 1.12.0 |
| safetensors | 0.7.0 |
| sentencepiece | 0.2.1 |
| protobuf | 7.34.1 |
| xformers | 0.0.35 |

Full exported records:

- `configs/clearread-llama-lora_environment.yml`
- `configs/clearread-llama-lora_pip_freeze.txt`

## Import Verification

Command:

```bash
ai/lora_training/scripts/check_wsl_training_env.sh --hf-check
```

Result:

- Overall environment check: pass
- `unsloth` import before `transformers` in a fresh Python process: pass
- Core imports passed: `torch`, `transformers`, `datasets`, `accelerate`, `peft`, `trl`, `bitsandbytes`, `unsloth`, `huggingface_hub`, `safetensors`, `sentencepiece`

Unsloth emitted this informational limitation:

```text
Unsloth: Your Flash Attention 2 installation seems to be broken. Using Xformers instead. No performance changes will be seen.
```

This is not a setup blocker because import and CUDA tests passed, and xformers is available.

## Hugging Face Access

- `hf` CLI available: yes, at `<conda-env-path>/clearread-llama-lora/bin/hf`
- `hf auth whoami`: failed with `Not logged in`
- Metadata-only model checks through `huggingface_hub.HfApi().model_info(...)`:

| Model ID | Metadata Accessible | Gated | SHA |
|---|---:|---|---|
| `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit` | yes | false | `3f09f44543858745a6af68161eded01dbcc536ad` |
| `unsloth/Llama-3.1-8B-Instruct-bnb-4bit` | yes | false | `26672447463f314a180021ded1522a55ce5b1090` |
| `meta-llama/Meta-Llama-3.1-8B-Instruct` | yes | manual | `0e9e39f249a16976918f6564b8830bc894c89659` |

No model weights were downloaded. No Hugging Face token was printed or saved.

## Known Limitations

- Hugging Face CLI is installed but not logged in. The preferred Unsloth model metadata is public and accessible, but official Meta gated model downloads will require an authenticated Hugging Face account with accepted access.
- Flash Attention 2 was not available or not healthy in this env; Unsloth fell back to xformers.
- The simple Unsloth pip route selected CUDA 12.8 runtime packages after the initial CUDA 12.6 PyTorch install. Runtime CUDA verification passed, so no fallback route was needed.

## Recommendation

Recommend central-brain review as pass with notes for Worker 003 environment setup. The environment is ready for Worker 004 smoke training script/config preparation, with the caveat that gated official Meta model access will need authentication if the project uses the official Meta fallback instead of the public Unsloth 4-bit model IDs.
