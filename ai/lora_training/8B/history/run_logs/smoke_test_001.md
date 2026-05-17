
# Smoke Test 001

Date/time: 2026-04-28T14:54:17+10:00

## Command

`python scripts/train_smoke_qlora.py --config ai/lora_training/configs/smoke_llama31_8b_qlora.example.yaml`

## Environment

- Python: `3.11.15`
- Platform: `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`
- Conda env: `clearread-llama-lora`

## Inputs

- Model id: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Data: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/smoke_test_10.jsonl`
- Data SHA256: `8f51d083e8fafae143ec146c0155f85dc23a5cfdaf931a04092e7f8543d2d3a8`
- Split manifest: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/split_manifest.json`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`

## Config

- Max sequence length: `3072`
- Per-device train batch size: `1`
- Gradient accumulation steps: `4`
- Max steps: `20`
- Learning rate: `0.0002`
- LoRA r/alpha/dropout: `16` / `32` / `0.05`
- Target modules: `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`

## Label Mask Summary

- Records: `10`
- Max input tokens: `1914`
- Total trainable assistant tokens: `1323`

## Progress Samples

| Step | Total | Elapsed | Avg Sec/Step | Remaining | ETA |
| --- | --- | --- | --- | --- | --- |
| 11 | 20 | 51s | 4.607 | 41s | 2026-04-28T14:54:20+10:00 |
| 12 | 20 | 53s | 4.403 | 35s | 2026-04-28T14:54:16+10:00 |
| 13 | 20 | 58s | 4.47 | 31s | 2026-04-28T14:54:17+10:00 |
| 14 | 20 | 1m 03s | 4.509 | 27s | 2026-04-28T14:54:18+10:00 |
| 15 | 20 | 1m 05s | 4.346 | 22s | 2026-04-28T14:54:14+10:00 |
| 16 | 20 | 1m 10s | 4.362 | 17s | 2026-04-28T14:54:15+10:00 |
| 17 | 20 | 1m 15s | 4.413 | 13s | 2026-04-28T14:54:16+10:00 |
| 18 | 20 | 1m 17s | 4.301 | 9s | 2026-04-28T14:54:14+10:00 |
| 19 | 20 | 1m 22s | 4.34 | 4s | 2026-04-28T14:54:14+10:00 |
| 20 | 20 | 1m 27s | 4.368 | 0s | 2026-04-28T14:54:15+10:00 |

## Result

- Status: `success`
- Elapsed runtime: `89.61` seconds

## Inference Sanity Check

Date/time: 2026-04-28T14:55:26+10:00
Adapter path: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/models/adapters/smoke_llama31_8b_qlora`
Examples checked: `3`
Schema pass count: `3`

| # | Schema OK | Reason | Output Preview |
| --- | --- | --- | --- |
| 1 | True | ok | {"main_idea":"The text explains nausea and vomiting and gives common causes, warning signs, diagnosis, and treatment. It says these symptoms are usually not ser |
| 2 | True | ok | {"main_idea":"The text explains infectious mononucleosis, or mono. It says EBV is the most common cause, and people can spread it through body fluids, so it's o |
| 3 | True | ok | {"main_idea":"The text explains how to report suspected tax fraud to the IRS. It says the IRS wants serious, well-supported cases and gives the form and mailing |

## Stage 005 Supplemental Audit

- Stage id: `Stage 005`
- Git branch before run: `feature/ai-llama-lora-training`
- Git commit before run: `e977769ab29fc7eb6242f5c32599d34eb7fc5cd2`
- OOM: `no`
- Adapter output path: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/models/adapters/smoke_llama31_8b_qlora`
- Final training loss: `0.5587`
- Final per-step loss logged at step 20: `0.02816`
- Trainer runtime: `87.37` seconds
- Script training elapsed runtime: `89.61` seconds
- Direct shell command wall time: about `237.4` seconds, including model load/cache work and adapter save.
- Trainer start time: about `2026-04-28T14:52:47+10:00`, derived from the smoke-log result timestamp minus the script training elapsed runtime.
- Training log/result timestamp: `2026-04-28T14:54:17+10:00`
- Inference check timestamp: `2026-04-28T14:55:26+10:00`

### Commands Run

```bash
python -m py_compile scripts/training_data_utils.py scripts/verify_assistant_loss_mask.py scripts/train_smoke_qlora.py scripts/run_inference_check.py
python scripts/verify_assistant_loss_mask.py --config configs/smoke_llama31_8b_qlora.example.yaml
python scripts/train_smoke_qlora.py --config configs/smoke_llama31_8b_qlora.example.yaml --dry-run
python scripts/train_smoke_qlora.py --config configs/smoke_llama31_8b_qlora.example.yaml
python scripts/run_inference_check.py --config configs/smoke_llama31_8b_qlora.example.yaml --num-examples 3
```

The WSL training commands were run inside conda env `clearread-llama-lora` from `ai/lora_training` with:

```bash
export HF_HOME=ai/lora_training/cache/huggingface
export TRANSFORMERS_CACHE=ai/lora_training/cache/huggingface/transformers
```

### Package Versions

| Package | Version |
| --- | --- |
| Python | `3.11.15` |
| torch | `2.10.0+cu128` |
| transformers | `5.5.0` |
| datasets | `4.3.0` |
| accelerate | `1.13.0` |
| peft | `0.19.1` |
| trl | `0.24.0` |
| bitsandbytes | `0.49.2` |
| unsloth | `2026.4.8` |
| huggingface_hub | `1.12.0` |
| safetensors | `0.7.0` |
| sentencepiece | `0.2.1` |

### GPU

- GPU: `NVIDIA GeForce RTX 4070 Ti SUPER`
- VRAM: `16376 MiB` reported by `nvidia-smi`; Unsloth reported max memory `15.992 GB`.
- Driver: `560.94`
- BF16: supported.
- CUDA: torch build `cu128`; Unsloth runtime reported CUDA Toolkit `12.8`.

### Adapter Files

| File | Size bytes | SHA256 |
| --- | ---: | --- |
| `adapter_config.json` | 1262 | `A78911EE5F9E9C50DB81F356B1A8963CFA0F001D10687CFA818A085902D25FE0` |
| `adapter_model.safetensors` | 167832240 | not recorded here; large model artifact, not package-ready |
| `chat_template.jinja` | 4614 | `E10CA381B1CCC5CF9DB52E371F3B6651576CAEE0A630B452E2816B2D404D4B65` |
| `README.md` | 5256 | `1DADFF2F9ED0BE94F4D1253AE61DE95DA79F7EDEA3D641FC157B9270B2C62612` |
| `tokenizer.json` | 17209920 | not recorded here; large tokenizer artifact, not committed |
| `tokenizer_config.json` | 50669 | `52A57D911C30CF2B645E3350AAFD9F1C424D2529483FD4628E7E34BFB33A7FE2` |

### ETA Summary

The ETA callback printed every step. The first step estimated about 2m 44s remaining, then stabilized quickly; by step 10 the ETA was about 46s remaining, and step 20 reported 0s remaining. Final average speed was about `4.368` seconds per step from the callback, while Hugging Face reported `0.229` train steps per second.

### Decision

Smoke training passed locally. The 20-step QLoRA run completed without OOM, saved the LoRA adapter, and inference passed schema checks for 3 of 3 smoke examples. The next model-selection review should verify logs, package-ready commit contents, and whether to proceed to full Candidate A training or adjust smoke settings first.

## Inference Sanity Check

Date/time: 2026-04-28T15:09:33+10:00
Adapter path: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/models/adapters/smoke_llama31_8b_qlora`
Examples checked: `3`
Schema pass count: `3`

| # | Schema OK | Reason | Output Preview |
| --- | --- | --- | --- |
| 1 | True | ok | {"main_idea":"The text explains nausea and vomiting and gives common causes, warning signs, diagnosis, and treatment. It says these symptoms are usually not ser |
| 2 | True | ok | {"main_idea":"The text explains infectious mononucleosis, or mono. It says EBV is the most common cause, and people can spread it through body fluids, so it's o |
| 3 | True | ok | {"main_idea":"The text explains how to report suspected tax fraud to the IRS. It says the IRS wants serious, well-supported cases and gives the form and mailing |
