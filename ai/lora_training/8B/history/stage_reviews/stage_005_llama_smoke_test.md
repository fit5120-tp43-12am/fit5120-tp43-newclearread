# Stage 005 Llama Smoke Test Log

Date/time: 2026-04-28T14:55:26+10:00

## Stage Reference

`Stage 005 Llama smoke test`

## Commands Run

From WSL inside conda env `clearread-llama-lora` and project directory `ai/lora_training`:

```bash
python -m py_compile scripts/training_data_utils.py scripts/verify_assistant_loss_mask.py scripts/train_smoke_qlora.py scripts/run_inference_check.py
python scripts/verify_assistant_loss_mask.py --config configs/smoke_llama31_8b_qlora.example.yaml
python scripts/train_smoke_qlora.py --config configs/smoke_llama31_8b_qlora.example.yaml --dry-run
python scripts/train_smoke_qlora.py --config configs/smoke_llama31_8b_qlora.example.yaml
python scripts/run_inference_check.py --config configs/smoke_llama31_8b_qlora.example.yaml --num-examples 3
```

Cache variables used:

```bash
export HF_HOME=ai/lora_training/cache/huggingface
export TRANSFORMERS_CACHE=ai/lora_training/cache/huggingface/transformers
```

## Training Result

- Training status: `success`
- OOM: `no`
- Model id used: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Smoke records: `10`
- Max steps: `20`
- Final training loss: `0.5587`
- Final step loss: `0.02816`
- Adapter path: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/models/adapters/smoke_llama31_8b_qlora`
- Smoke log: `ai/lora_training/history/run_logs/smoke_test_001.md`
- Run report: `ai/lora_training/reports/SMOKE_TRAINING_RUN_REPORT.md`

## Timing And ETA

- Script training elapsed runtime: `89.61` seconds
- Hugging Face trainer runtime: `87.37` seconds
- Direct shell command wall time: about `237.4` seconds, including model load/cache work and adapter save.
- Final callback average: `4.368` seconds per step.
- ETA behavior: progress printed every step. Early ETA was conservative, then stabilized; step 20 reported 0s remaining.

## Inference Result

- Inference command: `python scripts/run_inference_check.py --config configs/smoke_llama31_8b_qlora.example.yaml --num-examples 3`
- Examples checked: `3`
- Schema pass count: `3`
- Result: `ok`

## Adapter Artifact

Local adapter files:

| File | Size bytes | package-ready? |
| --- | ---: | --- |
| `adapter_config.json` | 1262 | metadata only |
| `adapter_model.safetensors` | 167832240 | no |
| `chat_template.jinja` | 4614 | metadata only |
| `README.md` | 5256 | metadata only |
| `tokenizer.json` | 17209920 | no |
| `tokenizer_config.json` | 50669 | metadata only |

Small metadata SHA256 hashes are recorded in `logs/smoke_test_001.md`. The `.safetensors` adapter file and tokenizer artifact are local model artifacts and must not be committed.

## Git Branch/Commit/Push Result

- Branch before run: `feature/ai-llama-lora-training`
- Commit before run: `e977769ab29fc7eb6242f5c32599d34eb7fc5cd2`
- Primary Git commit: `6e6b7bf174476dde7ed44488f29d024aaa44b561` (`docs(ai): record llama smoke test result`)
- Primary Git push: pushed to `origin/feature/ai-llama-lora-training`
- Follow-up Git commit/push: pending at this log revision so the pushed stage log can record the primary commit/push result.

## Blockers Or Deviations

- No training blocker.
- A first attempt to launch the training command as a background WSL process from PowerShell failed because `Start-Process` broke the `bash -lc` quoting before conda activation. It exited before training and before any adapter write. The required direct WSL training command was then run and succeeded.
- Unsloth reported the known Flash Attention 2 issue and used xformers fallback, consistent with Stage 003/004.
- Hugging Face requests were unauthenticated; no token was printed or saved.

## Recommendation

Recommend model-selection review and likely pass if independent checks confirm:

- `logs/smoke_test_001.md` and this stage log exist,
- the adapter exists locally,
- inference passed against the adapter,
- Git contains only package-ready logs/reports,
- no JSONL data or model/checkpoint artifacts were committed.
