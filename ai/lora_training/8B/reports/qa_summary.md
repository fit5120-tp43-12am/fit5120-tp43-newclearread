# LoRA Training QA Summary

This summary collects the main verification evidence for the ClearRead Llama LoRA training package.

## Data And Split QA

| Check | Result |
| --- | --- |
| Accepted source records | 1452 |
| Domains covered | 7 |
| Train/validation/test split | 1162 / 145 / 145 |
| Split method | Deterministic approximate joint stratification over `domain x natural_length_bucket` |
| Split overlap | No train/validation/test overlap |
| Smoke set | 10 records, selected from train only |
| Manifest raw text fields | Not included |
| Source data mutation | Source files treated as read-only |

## Label-Masking QA

| Check | Result |
| --- | --- |
| Training target | Assistant JSON completion only |
| System/user labels | Masked with `-100` |
| Smoke records with trainable assistant tokens | 10 |
| Smoke truncated records | 0 |
| Mask method | Token-prefix masking with fallback support |

## Environment QA

| Check | Result |
| --- | --- |
| CUDA visible | Passed |
| CUDA tensor execution | Passed |
| BF16 support | Available |
| Core package imports | Passed |
| Flash Attention 2 | Unavailable, xformers fallback accepted |
| Hugging Face token exposure | No token printed or saved |

## Training QA

| Phase | Result |
| --- | --- |
| Smoke training | Success, no OOM |
| Smoke inference sanity | 3/3 schema pass |
| Full Candidate A training | Success, no OOM |
| Full training epochs | 3 |
| Optimizer steps | 438 |
| Final train loss | 0.4797596574748216 |
| Validation loss | 0.9654271602630615 |
| Post-training validation sanity | 10/10 schema pass |

## Evaluation QA

| Evaluation | Result |
| --- | --- |
| Validation records | 145 |
| Validation JSON parse | 145/145 |
| Validation schema pass | 145/145 |
| Validation manual review | pass 14, minor issue 2, major issue 0, uncertain 0 |
| Final test records | 145 |
| Final test JSON parse | 145/145 |
| Final test schema pass | 144/145 |
| Final test manual review | pass 14, minor issue 2, major issue 1, uncertain 0 |

## Final Decision

Candidate A was selected. Candidate B was skipped because validation evidence did not justify a second candidate, and tuning after looking at the held-out test would contaminate the final evaluation.

The final test found one schema-contract issue where an output had seven key points instead of exactly four. Deployment therefore requires the schema guard implemented in `scripts/infer_clearread_candidate_a.py`.
