# Stage 1 Interim Summary v2 - 2026-05-12

## Scope

All new experiment files are isolated under:

`<local-3b-search-workspace>`

The old `iteration1` and `training-3b` folders are read-only sources.

## Completed Anchor Runs

All completed Stage 1 anchor runs use SFT + 4-bit QLoRA, r=32, alpha=64, dropout=0.05, learning rate 2e-4, max sequence length 3072, effective batch size 8, and epoch snapshots 1-5.

| Model | Runtime | Best parse | Best judge mean | Tentative selected checkpoint |
|---|---:|---:|---:|---:|
| Llama 3.2 3B Instruct | 11,306.21 sec | 140/145 | 75.56 | epoch 2 |
| Granite 4.1 3B | 7,780.29 sec | 141/145 | 75.914894 | epoch 2 |
| Phi-4 mini instruct | 7,217.86 sec | 141/145 | 78.54 | epoch 3 |
| Ministral 3 3B Instruct | about 5,951 sec | 141/145 | 75.94 | epoch 5 |

Phi-4 mini instruct epoch 3 remains the strongest completed Stage 1 checkpoint so far. This is not final because Qwen is still running and Gemma still needs a full fallback run or a documented feasibility decision.

## Semantic-Rescue Backfill

Semantic-rescue samples were backfilled for the four completed models. Most parse failures look like format-only failures rather than inability to summarize:

- Llama: all sampled failures across epochs 1-5 were classified as likely format-only failures.
- Granite: all sampled failures across epochs 1-5 were classified as likely format-only failures.
- Ministral: all sampled failures across epochs 1-5 were classified as likely format-only failures.
- Phi: all sampled failures were likely format-only except one epoch 4 item classified as refusal/meta.

These labels are deterministic heuristics for documentation, not replacements for judge scoring.

## Running / Pending

| Model | Status | Notes |
|---|---|---|
| Qwen 3.5 4B | running | Stage 1 anchor has saved epochs 1 and 2 and is continuing toward epoch 5. |
| Gemma 4 E4B it | pending | Smoke test showed default batch=2 OOM; fallback batch=1 and grad accumulation=8 can run but is very slow. |

## Pipeline Updates

Generic scripts were added for Stage 3 and Stage 4 so every future training run has the same recorded flow: training with OOM fallback, full validation, semantic-rescue sample, fixed 50-item judge subset, judge aggregation, and checkpoint selection.
