# phi4_mini_instruct Checkpoint Selection

- Candidate: `phi4_mini_instruct`
- Base model: `microsoft/Phi-4-mini-instruct`
- Run id: `phase2_r32_a64_lr1e4`
- Stage label: `phase2_r32_a64_lr1e4`
- Selected epoch: `4`
- Selected adapter retained externally: `<external-local-raw-phase2-search-workspace-not-in-git>/model_workspaces/phi4_mini_instruct/models/adapters/phase2_r32_a64_lr1e4_selected_epoch_4`

## Selection Rule

The checkpoint is selected by product readiness first, then capped judge score, source safety margin, main message salience, and lower severe/major risk count.

## Epoch Results

| Epoch | Parsed OK | Judge mean | Judge count | Source safety | Main salience | Severe risk | Major risk |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 133/145 | 76.755102 | 49 | 3.326531 | 4.183673 | 0 | 4 |
| 2 | 140/145 | 74.94 | 50 | 3.2 | 4.12 | 0 | 2 |
| 3 | 139/145 | 74.4 | 50 | 3.24 | 4.16 | 0 | 6 |
| 4 | 140/145 | 77.306122 | 49 | 3.285714 | 4.163265 | 0 | 4 |
| 5 | 138/145 | 75.530612 | 49 | 3.22449 | 4.081633 | 1 | 1 |

## Rationale

Epoch 4 was selected because it ranked highest under the stated rule.
