# Final Model Selection Report

Last updated: 2026-04-28

## Selection

Selected model: Candidate A.

- Base model: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Training route: Llama-3.1-8B-Instruct + SFT + QLoRA
- Adapter: `models/adapters/full_candidate_a_3epoch`
- Final local metadata: `models/final/clearread_llama31_8b_qlora_candidate_a`
- Training config: `configs/train_llama31_8b_qlora_candidate_a.example.yaml`

## Why Candidate A Was Selected

Candidate A completed the approved 3-epoch full training run without OOM, passed validation schema checks, passed a full validation quality audit, and performed strongly on the final held-out test. It produced no detected markdown/code-fence leakage, extra text outside JSON, refusal/meta-response behavior, prediction mojibake, or broad domain/length collapse.

Candidate B was skipped because the validation audit did not justify another candidate, and using the held-out test schema miss to train or tune a replacement would contaminate the final evaluation.

## Training Summary

- Epochs: `3`
- Optimizer steps: `438`
- Final train loss: `0.4797596574748216`
- Validation loss: `0.9654271602630615`
- OOM: `no`
- Validation inference sanity after training: `10/10` schema pass

## Validation Metrics

Validation audit on `data/splits/val.jsonl`:

- Records: `145`
- JSON parse: `145/145`
- Schema pass: `145/145`
- Exact key order: `145/145`
- Exactly 4 key points: `145/145`
- Main idea two-sentence heuristic: `144/145`
- Each key point one-sentence heuristic: `143/145`
- Prediction mojibake rows: `0`
- Gold mojibake rows: `0`
- Manual review: `pass` 14, `minor_issue` 2, `major_issue` 0, `uncertain` 0

Validation manual review found no instruction-following failures, no refusal/meta behavior, no mojibake, and no broad quality collapse. The two minor issues were isolated precision or wording concerns.

## Final Test Metrics

Final held-out test on `data/splits/test.jsonl`:

- Records: `145`
- JSON parse: `145/145`
- Schema pass: `144/145`
- Exact key order: `145/145`
- Main idea string: `145/145`
- Key points list: `145/145`
- Exactly 4 key points: `144/145`
- All key points strings: `145/145`
- Main idea two-sentence heuristic: `144/145`
- Each key point one-sentence heuristic: `144/145`
- Empty-string rows: `0`
- Output too short / too long: `0 / 0`
- Markdown/code-fence leakage: `0`
- Extra text outside JSON: `0`
- Refusal/meta-response phrases: `0`
- Prediction mojibake rows: `0`
- Gold mojibake rows: `0`

Manual review labels: `pass` 14, `minor_issue` 2, `major_issue` 1, `uncertain` 0.

## Row 87 Caveat And Guard Decision

The only final-test schema failure was row 87:

- Domain: `academic_paper`
- Natural length bucket: `medium`
- Record ID: `academic_paper:000458:8541ac16b79f`
- Schema error: `key_points_len_7`

The content was broadly faithful, but the output violated the exact contract by producing seven key points. Deployment therefore requires a schema guard. The local inference wrapper validates key order, value types, and key-point count before returning output. If a parseable output has more than four key points, it returns only the first four generated key points and records `schema_guard_action: truncated_key_points` in debug metadata. If the output is not parseable or has too few key points, wrong keys, or wrong value types, it returns a machine-readable error object.

This guard is a deployment safety layer, not a change to the final held-out test result.

## Remaining Risks

- The raw adapter is not perfectly schema compliant without a wrapper.
- The validation loss is higher than the train loss, so future deployments should keep monitoring faithfulness and concise output quality.
- Manual review found two minor final-test issues: one public-service omission around processing time and one general-knowledge timing/detail fusion.
- The wrapper currently rejects under-length key-point lists instead of retrying; callers should surface the error or implement a controlled retry policy outside model-selection evaluation.

## Next Integration Steps

1. Use `docs/local_inference_runbook.md` to run local inference from WSL.
2. Integrate `scripts/infer_clearread_candidate_a.py` as the local safety wrapper around Candidate A.
3. Preserve the selected adapter in `models/adapters/full_candidate_a_3epoch`; keep adapter and model weights in external artifact storage.
4. For application integration, consume only successful final JSON outputs or handle the wrapper's machine-readable error object.
