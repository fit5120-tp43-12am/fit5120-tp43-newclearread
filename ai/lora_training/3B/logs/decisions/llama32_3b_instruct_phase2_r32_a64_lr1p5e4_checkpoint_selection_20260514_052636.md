# llama32_3b_instruct Checkpoint Selection

- Candidate: `llama32_3b_instruct`
- Base model: `unsloth/Llama-3.2-3B-Instruct-bnb-4bit`
- Run id: `phase2_r32_a64_lr1p5e4`
- Stage label: `phase2_r32_a64_lr1p5e4`
- Selected epoch: `4`
- Selected adapter copy: `model_workspaces/llama32_3b_instruct/models/adapters/phase2_r32_a64_lr1p5e4_selected_epoch_4`

## Selection Rule

The checkpoint is selected by product readiness first, then capped judge score, source safety margin, main message salience, and lower severe/major risk count.

## Epoch Results

| Epoch | Parsed OK | Judge mean | Judge count | Source safety | Main salience | Severe risk | Major risk |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 141/145 | 75.12 | 50 | 3.14 | 4.08 | 0 | 4 |
| 4 | 141/145 | 76.46 | 50 | 3.22 | 4.04 | 0 | 4 |
| 5 | 141/145 | 71.2 | 50 | 2.96 | 3.84 | 2 | 1 |

## Rationale

Epoch 4 was selected because it ranked highest under the stated rule.
