# Worker 003 WSL Environment Setup

Date/time: 2026-04-28 14:08:17 +10:00

Status: executed, pending central-brain review.

## Work Order

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\work_orders\003_setup_wsl_training_environment.md
```

## Command Summary

Read required project context:

```powershell
Get-Content -LiteralPath 'C:\Users\Aufb\Desktop\fit5120\iteration1\training\TRAINING_MEMORY.md' -Raw
Get-Content -LiteralPath 'C:\Users\Aufb\Desktop\fit5120\iteration1\training\docs\CENTRAL_BRAIN_WORKER_PROTOCOL.md' -Raw
Get-Content -LiteralPath 'C:\Users\Aufb\Desktop\fit5120\iteration1\training\docs\MASTER_TRAINING_PLAN.md' -Raw
Get-Content -LiteralPath 'C:\Users\Aufb\Desktop\fit5120\iteration1\training\logs\decisions\central_review_worker_002.md' -Raw
```

Consulted current docs:

```text
https://unsloth.ai/docs/get-started/install/pip-install
https://unsloth.ai/docs/get-started/fine-tuning-llms-guide
https://huggingface.co/docs/trl/sft_trainer
https://pytorch.org/get-started/locally/
```

Inspected WSL/conda/GPU:

```powershell
wsl.exe -e bash -lc 'source /home/aufb/miniconda3/etc/profile.d/conda.sh; conda --version; conda env list'
```

Created environment and installed packages:

```bash
source /home/aufb/miniconda3/etc/profile.d/conda.sh
conda create -y -n clearread-llama-lora python=3.11 pip
conda activate clearread-llama-lora
python -m pip install --upgrade pip setuptools wheel packaging ninja cmake
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
python -m pip install unsloth huggingface_hub safetensors sentencepiece protobuf
```

Exported environment records:

```bash
conda env export -n clearread-llama-lora --no-builds > configs/clearread-llama-lora_environment.yml
conda run -n clearread-llama-lora python -m pip freeze > configs/clearread-llama-lora_pip_freeze.txt
```

Verified environment:

```bash
/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training/scripts/check_wsl_training_env.sh --hf-check
```

## Environment Creation Status

- Env name: `clearread-llama-lora`
- Env path: `/home/aufb/miniconda3/envs/clearread-llama-lora`
- Python: 3.11.15
- Old env `/home/aufb/miniconda3/envs/dyslexia-summary` was not modified.
- Old project `/home/aufb/dyslexia_summary_ai` was not modified.

## Verification Summary

- WSL distro: Ubuntu 24.04.4 LTS, WSL2
- GPU: NVIDIA GeForce RTX 4070 Ti SUPER
- Driver: 560.94
- `torch.__version__`: 2.10.0+cu128
- `torch.version.cuda`: 12.8
- `torch.cuda.is_available()`: true
- CUDA device count: 1
- BF16 support: true
- CUDA tensor test: passed
- Unsloth-before-Transformers fresh process import: passed
- Required package imports: passed

Core package versions:

- `transformers`: 5.5.0
- `datasets`: 4.3.0
- `accelerate`: 1.13.0
- `peft`: 0.19.1
- `trl`: 0.24.0
- `bitsandbytes`: 0.49.2
- `unsloth`: 2026.4.8
- `huggingface_hub`: 1.12.0
- `safetensors`: 0.7.0
- `sentencepiece`: 0.2.1

## Hugging Face Summary

- `hf` CLI is available.
- `hf auth whoami` reports not logged in.
- Metadata-only access succeeded for:
  - `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
  - `unsloth/Llama-3.1-8B-Instruct-bnb-4bit`
  - `meta-llama/Meta-Llama-3.1-8B-Instruct`
- The official Meta model metadata reports `gated = manual`.
- No token was printed or saved.
- No model weights were downloaded.

## Git Result

Initial repo check before Worker 003 repo-side changes:

- Branch: `feature/ai-llama-lora-training`
- Local HEAD: `b5177957f8857004d02ed309d4ec50a709fdf8e9`
- Upstream HEAD: `b5177957f8857004d02ed309d4ec50a709fdf8e9`
- Worktree: clean

Final commit/push result: pending at the time this initial log was written; to be updated after Git-safe files are mirrored, committed, and pushed.

## Blockers Or Deviations

- No environment setup blocker.
- Hugging Face CLI is not logged in. This is recorded as a limitation for gated official Meta fallback access.
- Unsloth reported Flash Attention 2 as broken and fell back to xformers. This is not a blocker for the next smoke-script worker.
- The initial PyTorch CUDA 12.6 install was superseded by the simple Unsloth pip route, which selected `torch 2.10.0+cu128`. CUDA runtime verification passed.

## Recommendation

Recommend central-brain review as pass with notes. Next worker should prepare smoke training scripts/configs and include assistant-token-only loss masking checks before any model training.
