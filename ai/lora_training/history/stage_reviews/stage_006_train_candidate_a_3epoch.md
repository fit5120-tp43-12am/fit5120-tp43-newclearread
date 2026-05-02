# Stage 006 Train Candidate A 3 Epoch

Date/time: 2026-04-28T16:37:14+10:00

## Stage Reference

`Stage 006 Candidate A full training`

## Files Created Or Changed

- `configs\train_llama31_8b_qlora_candidate_a.yaml`
- `scripts\train_full_qlora.py`
- `scripts\run_inference_check.py`
- `logs\full_train_candidate_a_3epoch.md`
- `reports\FULL_TRAIN_CANDIDATE_A_REPORT.md`
- `logs\decisions\stage_006_train_candidate_a_3epoch.md`
- `TRAINING_MEMORY.md` will receive a provisional Stage 006 update.

## Commands Run

```bash
python -m py_compile scripts/training_data_utils.py scripts/verify_assistant_loss_mask.py scripts/train_full_qlora.py scripts/run_inference_check.py
python scripts/train_full_qlora.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --dry-run
python scripts/train_full_qlora.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml
python scripts/run_inference_check.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --adapter-path models/adapters/full_candidate_a_3epoch --data-path data/splits/val.jsonl --num-examples 10
```

All training/inference commands were run in WSL env `clearread-llama-lora` from `ai/lora_training` with the project-local Hugging Face cache variables.

A first background launch attempt through Windows `Start-Process wsl.exe` did not enter training or create stdout/stderr/exitcode files. This matched the known Stage 005 quoting issue, so the actual training was run directly through WSL.

## Preflight Result

Status: `passed`

- Train records: `1162`
- Validation records: `145`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- Train SHA256: `b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb`
- Validation SHA256: `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be`
- Max train input tokens: `2296`
- Max validation input tokens: `2171`
- Max train assistant tokens: `192`
- Max validation assistant tokens: `204`
- Total trainable assistant tokens: `167656`
- Train truncated records: `0`
- Validation truncated records: `0`
- Every record had non-empty assistant trainable labels.
- Decoded trainable labels parsed as JSON for all train and validation records.

## Training Result

Status: `success`

- Model id: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Epochs: `3`
- Optimizer steps: `438`
- OOM: `no`
- Final train loss: `0.4797596574748216`
- Validation loss: `0.9654271602630615`
- Validation loss method: final `trainer.evaluate(eval_dataset=validation)`.
- Adapter path: `models/adapters/full_candidate_a_3epoch`
- Output path: `outputs/full/candidate_a_3epoch`

## Validation Inference Result

Status: `passed`

- Data path: `data/splits/val.jsonl`
- Examples checked: `10`
- Schema pass: `10/10`

## Timing And ETA

- Training start: `2026-04-28T15:29:34+10:00`
- Training end: `2026-04-28T16:34:13+10:00`
- Script training elapsed: `1h 04m 39s`
- Trainer runtime: `3801.7851` seconds
- Final progress callback average: `8.68` seconds per optimizer step
- ETA behavior: early estimates were conservative, then stabilized near the actual completion window.

## Git Result

- Branch: `feature/ai-llama-lora-training`
- Commit before Stage 006 run: `4c49a33aeb5c5d7816560d95e293db40c4e5f4e6`
- Primary commit pushed: `cdba362f2754b827a0d9204e966d0b27f7a1d85b`
- Primary commit message: `feat(ai): train candidate a qlora workflow`
- Push target: `origin/feature/ai-llama-lora-training`
- After primary push, local HEAD equaled upstream at `cdba362f2754b827a0d9204e966d0b27f7a1d85b`.
- `git ls-files 'ai/**/*.jsonl'` returned empty.
- `git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin'` returned empty.
- Follow-up docs/log commit pushed: `7a637a8195d1b708bf482a5dcd48ca0bd68cb402` (`docs(ai): record stage 006 training result`).
- After that follow-up push, local HEAD equaled upstream at `7a637a8195d1b708bf482a5dcd48ca0bd68cb402`.

## Blockers Or Deviations

- No training blocker.
- No OOM.
- No truncation.
- No test set use.
- Background WSL launch via `Start-Process` failed before training and was replaced by the direct required WSL command.
- Two train records did not exactly match source assistant JSON after tokenizer decode because `.gov` spacing was normalized; this was recorded as evidence, not treated as label loss because there was no truncation and decoded labels remained valid JSON.

## Recommendation

Recommend model-selection review. Candidate A is viable for later evaluation review. Candidate B should not be automatic from this stage's evidence; consider it only if project review qualitative validation review finds weak output quality or overfitting concerns.
