# ministral3_3b_instruct Checkpoint Selection

- Candidate: `ministral3_3b_instruct`
- Base model: `mistralai/Ministral-3-3B-Instruct-2512-BF16`
- Run id: `phase2_r32_a64_lr1p5e4`
- Stage label: `phase2_r32_a64_lr1p5e4`
- Selected epoch: `3`
- Selected adapter copy: `model_workspaces/ministral3_3b_instruct/models/adapters/phase2_r32_a64_lr1p5e4_selected_epoch_3`

## Selection Rule

The checkpoint is selected by product readiness first, then capped judge score, source safety margin, main message salience, and lower severe/major risk count.

## Epoch Results

| Epoch | Parsed OK | Judge mean | Judge count | Source safety | Main salience | Severe risk | Major risk |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 143/145 | 73.959184 | 49 | 3.102041 | 4.102041 | 1 | 3 |
| 4 | 142/145 | 75.28 | 50 | 3.26 | 4.04 | 0 | 4 |
| 5 | 143/145 | 72.74 | 50 | 3.12 | 4.12 | 1 | 4 |

## Rationale

Epoch 3 was selected because it ranked highest under the stated rule.
