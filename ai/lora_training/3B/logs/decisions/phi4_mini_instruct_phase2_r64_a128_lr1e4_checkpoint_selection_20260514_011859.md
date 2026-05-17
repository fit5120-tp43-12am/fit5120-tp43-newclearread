# phi4_mini_instruct Checkpoint Selection

- Candidate: `phi4_mini_instruct`
- Base model: `microsoft/Phi-4-mini-instruct`
- Run id: `phase2_r64_a128_lr1e4`
- Stage label: `phase2_r64_a128_lr1e4`
- Selected epoch: `5`
- Selected adapter retained externally: `<external-local-raw-phase2-search-workspace-not-in-git>/model_workspaces/phi4_mini_instruct/models/adapters/phase2_r64_a128_lr1e4_selected_epoch_5`

## Selection Rule

The checkpoint is selected by product readiness first, then capped judge score, source safety margin, main message salience, and lower severe/major risk count.

## Epoch Results

| Epoch | Parsed OK | Judge mean | Judge count | Source safety | Main salience | Severe risk | Major risk |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 136/145 | 75.897959 | 49 | 3.142857 | 4.0 | 0 | 1 |
| 2 | 138/145 | 74.96 | 50 | 3.1 | 4.0 | 0 | 2 |
| 3 | 137/145 | 75.36 | 50 | 3.24 | 4.06 | 0 | 4 |
| 4 | 138/145 | 74.42 | 50 | 3.1 | 3.98 | 0 | 5 |
| 5 | 139/145 | 72.34 | 50 | 3.06 | 3.94 | 0 | 7 |

## Rationale

Epoch 5 was selected because it ranked highest under the stated rule.
