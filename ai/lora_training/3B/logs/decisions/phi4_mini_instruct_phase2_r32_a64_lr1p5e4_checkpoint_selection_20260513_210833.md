# phi4_mini_instruct Checkpoint Selection

- Candidate: `phi4_mini_instruct`
- Base model: `microsoft/Phi-4-mini-instruct`
- Run id: `phase2_r32_a64_lr1p5e4`
- Stage label: `phase2_r32_a64_lr1p5e4`
- Selected epoch: `3`
- Selected adapter retained externally: `<external-local-raw-phase2-search-workspace-not-in-git>/model_workspaces/phi4_mini_instruct/models/adapters/phase2_r32_a64_lr1p5e4_selected_epoch_3`

## Selection Rule

The checkpoint is selected by product readiness first, then capped judge score, source safety margin, main message salience, and lower severe/major risk count.

## Epoch Results

| Epoch | Parsed OK | Judge mean | Judge count | Source safety | Main salience | Severe risk | Major risk |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 137/145 | 74.28 | 50 | 3.24 | 4.1 | 0 | 5 |
| 2 | 137/145 | 74.58 | 50 | 3.24 | 4.1 | 1 | 3 |
| 3 | 140/145 | 80.28 | 50 | 3.38 | 4.3 | 0 | 1 |
| 4 | 140/145 | 76.285714 | 49 | 3.265306 | 4.122449 | 0 | 2 |
| 5 | 139/145 | 76.081633 | 49 | 3.22449 | 4.102041 | 0 | 4 |

## Rationale

Epoch 3 was selected because it ranked highest under the stated rule.
