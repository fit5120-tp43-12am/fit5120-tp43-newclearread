# Smoke Training Run Report

Date/time: 2026-04-28T14:55:26+10:00

## Scope

The smoke-training step ran the first real ClearRead Llama-3.1-8B-Instruct smoke training test on the approved 10-record smoke split, saved a local QLoRA adapter, and ran inference sanity checks against that adapter.

## Result

- Status: `success`
- OOM: `no`
- Model id: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Adapter path: `models/adapters/smoke_llama31_8b_qlora`
- Smoke data SHA256: `8f51d083e8fafae143ec146c0155f85dc23a5cfdaf931a04092e7f8543d2d3a8`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- Max input tokens from dry-run: `1914`
- Max trainable assistant tokens from dry-run: `164`
- Total trainable assistant tokens from mask check: `1323`
- Truncated records: `0`
- Final training loss: `0.5587`
- Final step loss: `0.02816`
- Trainer runtime: `87.37` seconds
- Script training elapsed runtime: `89.61` seconds
- Average callback speed at final step: `4.368` seconds per step

## Config

- Max sequence length: `3072`
- QLoRA: 4-bit NF4
- LoRA r/alpha/dropout: `16 / 32 / 0.05`
- Target modules: `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`
- Per-device batch size: `1`
- Gradient accumulation steps: `4`
- Effective batch size: `4`
- Max steps: `20`
- Learning rate: `0.0002`
- Assistant-only loss masking: enabled and verified.

## Environment

- Conda env: `clearread-llama-lora`
- Python: `3.11.15`
- GPU: `NVIDIA GeForce RTX 4070 Ti SUPER`
- VRAM: `16376 MiB`
- Driver: `560.94`
- BF16: supported
- torch: `2.10.0+cu128`
- transformers: `5.5.0`
- datasets: `4.3.0`
- accelerate: `1.13.0`
- peft: `0.19.1`
- trl: `0.24.0`
- bitsandbytes: `0.49.2`
- unsloth: `2026.4.8`
- huggingface_hub: `1.12.0`
- safetensors: `0.7.0`
- sentencepiece: `0.2.1`

## Inference Sanity Check

Command:

```bash
python scripts/run_inference_check.py --config configs/smoke_llama31_8b_qlora.example.yaml --num-examples 3
```

Result:

- Examples checked: `3`
- Schema pass count: `3`
- Valid JSON shape: `3/3`
- Required keys `main_idea` and `key_points`: `3/3`

The output previews in `logs/smoke_test_001.md` show the adapter produced concise JSON summaries for the three checked smoke examples.

## Safety

- The source datasets and approved split files were not modified.
- The adapter and tokenizer artifacts were kept local under `models/adapters/smoke_llama31_8b_qlora`.
- Hugging Face cache files were kept under `cache/huggingface`.
- Full data JSONL files, base model files, adapter `.safetensors`, checkpoints, `.pt`, `.pth`, and `.bin` files are large runtime artifacts and are not included in this package.

## Notes

- Unsloth again reported Flash Attention 2 as broken and used xformers fallback, consistent with the earlier environment and preparation checks.
- A first attempt to launch training as a background process from PowerShell failed because `Start-Process` broke the WSL `bash -lc` quoting before conda activation. No training or adapter write occurred in that failed launch. The required training command was then run directly through WSL and succeeded.

## Recommendation

The smoke run passed the required checks. The next stage was full Candidate A training using the approved train/validation split.
