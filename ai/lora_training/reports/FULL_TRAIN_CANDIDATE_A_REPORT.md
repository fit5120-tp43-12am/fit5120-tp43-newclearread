# Full Train Candidate A Report

Date/time: 2026-04-28T16:37:14+10:00

## Summary

Candidate A completed successfully.

- Model: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Method: `SFT + QLoRA`
- Epochs: `3`
- Optimizer steps: `438`
- OOM: `no`
- Adapter: `models/adapters/full_candidate_a_3epoch`
- Training log: `logs/full_train_candidate_a_3epoch.md`

Candidate A should be considered a viable candidate for later project review and possible final evaluation. Do not use the test set until the the project selects the final model candidate.

## Preflight

The required train/validation tokenization gate passed before full training.

| Split | Records | SHA256 | Max Input Tokens | Max Assistant Tokens | Total Assistant Tokens | Truncated | Non-Empty Labels | JSON OK |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 1162 | `b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb` | 2296 | 192 | 148979 | 0 | 1162 | 1162 |
| validation | 145 | `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be` | 2171 | 204 | 18677 | 0 | 145 | 145 |

Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`.

Note: train had 2 decoded-label exact JSON object mismatches caused by tokenizer decode spacing around `.gov`; both decoded labels still parsed as JSON, had non-empty labels, and had no truncation.

## Losses

- Final train loss: `0.4797596574748216`
- Validation loss: `0.9654271602630615`
- Validation loss method: `trainer.evaluate(eval_dataset=validation)` once after training.

The train/validation gap should be reviewed, but schema sanity was strong on the sampled validation examples.

## Validation Sanity

Validation inference command:

```bash
python scripts/run_inference_check.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --adapter-path models/adapters/full_candidate_a_3epoch --data-path data/splits/val.jsonl --num-examples 10
```

Result:

- Examples checked: `10`
- Schema pass: `10/10`
- Required keys and JSON shape: passed for all checked examples.

## Timing

- Training start: `2026-04-28T15:29:34+10:00`
- Training end: `2026-04-28T16:34:13+10:00`
- Script training elapsed runtime: `1h 04m 39s`
- Final ETA callback average: `8.68` seconds per optimizer step
- Trainer runtime: `3801.7851` seconds
- Validation evaluation runtime: `75.1215` seconds

Early ETA estimates were conservative while the run warmed up; later estimates stabilized and finished close to the actual completion window.

## Recommendation

Candidate A is viable for validation review. Candidate B is not recommended at this stage because Candidate A completed cleanly and passed `10/10` validation schema checks. Candidate B should only be considered if later quality review finds weak summaries, overfitting concerns, or poor behavior on broader validation samples.
