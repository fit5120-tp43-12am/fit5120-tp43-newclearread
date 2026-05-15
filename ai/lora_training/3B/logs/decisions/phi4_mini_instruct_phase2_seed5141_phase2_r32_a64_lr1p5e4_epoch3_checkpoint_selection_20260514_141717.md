# phi4_mini_instruct Checkpoint Selection

- Candidate: `phi4_mini_instruct`
- Base model: `microsoft/Phi-4-mini-instruct`
- Run id: `phase2_seed5141_phase2_r32_a64_lr1p5e4_epoch3`
- Stage label: `phase2_seed5141_phase2_r32_a64_lr1p5e4_epoch3`
- Selected epoch: `5`
- Selected adapter copy: `model_workspaces/phi4_mini_instruct/models/adapters/phase2_seed5141_phase2_r32_a64_lr1p5e4_epoch3_selected_epoch_5`

## Selection Rule

The checkpoint is selected by product readiness first, then capped judge score, source safety margin, main message salience, and lower severe/major risk count.

## Epoch Results

| Epoch | Parsed OK | Judge mean | Judge count | Source safety | Main salience | Severe risk | Major risk |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 141/145 | 78.46 | 50 | 3.26 | 4.02 | 0 | 3 |
| 5 | 142/145 | 75.58 | 50 | 3.24 | 4.08 | 0 | 3 |

## Rationale

Epoch 5 was selected because it ranked highest under the stated rule.
