# Model Training And Validation Search Report

## Project Purpose

This report explains the model-training search used to find a 3B-scale replacement candidate for the existing ClearRead 8B summarisation model. The goal was to preserve practical summary quality while reducing deployment footprint.

## Work Completed

The search had three main phases.

| Phase | Work |
|---|---|
| Llama-only optimisation | Tested Llama 3.2 3B training and prompt-control variants, including r32, r64, continuation epochs, and prompt guards. |
| Stage 1 anchor search | Trained several 3B-4B model families with a common 5-epoch QLoRA anchor setup. |
| Phase2 compressed search | Focused on Phi-4-mini, Llama 3.2 3B, and Ministral using validation results and hard selection rules. |

The common anchor setup used SFT + QLoRA, 4-bit loading where supported, LoRA rank 32, alpha 64, dropout 0.05, learning rate 2e-4, max sequence length 3072, effective batch size 8, and epoch snapshots from 1 to 5.

## Rationale

The first Llama-only pass tested whether a smaller Llama model could approach the 8B baseline through training and inference controls. The result improved the 3B score, then indicated value in testing other 3B-4B model families.

The broader anchor search gave each candidate a fair starting curve. The compressed Phase2 search reduced unnecessary runs after Phi, Llama, and Ministral became the main practical contenders.

## Verification Results

### Llama-Only Optimisation

| Experiment | Parsed | Mean score |
|---|---:|---:|
| Original 3B Candidate B epoch 4 | 139/145 | 71.927536 |
| r32 epoch 4 + prompt guard v2 | 141/145 | 71.418440 |
| r64 epoch 1 + original prompt | 140/145 | 72.450000 |
| r64 epoch 1 + prompt guard v2 | 143/145 | 72.118881 |
| r64 epoch 1 + gentle parser guard v3 | 140/145 | 73.835714 |

The strongest Llama-only pass reached 73.835714, which improved over the first 3B result.

### Stage 1 Anchor Search

| Model | Runtime | Best parse | Best judge mean | Tentative checkpoint |
|---|---:|---:|---:|---:|
| Llama 3.2 3B Instruct | 11,306.21 sec | 140/145 | 75.56 | epoch 2 |
| Granite 4.1 3B | 7,780.29 sec | 141/145 | 75.914894 | epoch 2 |
| Phi-4-mini | 7,217.86 sec | 141/145 | 78.54 | epoch 3 |
| Ministral 3B | about 5,951 sec | 141/145 | 75.94 | epoch 5 |

Phi-4-mini produced the strongest Stage 1 validation signal. Llama and Ministral remained strong enough for continued local comparison.

### Phase2 Compressed Search

| Rank | Candidate | Config | Epoch | Val50 score | Parsed | Severe | Major |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | Phi-4-mini | r32 alpha64 lr1.5e-4 | 3 | 80.28 | 140/145 | 0 | 1 |
| 2 | Phi-4-mini | r32 alpha64 lr1e-4 | 4 | 77.306122 | 140/145 | 0 | 4 |
| 3 | Llama 3.2 3B | r32 alpha64 lr1.5e-4 | 4 | 76.46 | 141/145 | 0 | 4 |
| 7 | Ministral 3B | r32 alpha64 lr1.5e-4 | 4 | 75.28 | 142/145 | 0 | 4 |

The final Llama checkpoint selected for benchmark was:

| Field | Value |
|---|---|
| Base model | `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` |
| Adapter | `phase2_r32_a64_lr1p5e4_epoch_4` |
| Rank / alpha / dropout | `r=32`, `alpha=64`, `dropout=0.05` |
| Learning rate | `1.5e-4` |
| Selected epoch | 4 |

## Deployment Observations And Handling

The training phase exposed several engineering issues. A continuation run required a corrected gradient-checkpointing runner. One selected adapter directory first contained only a manifest, so adapter files were copied into the selected directory and the run was repeated. A validation run used a continuation-only setup, so the runner was corrected and validation was repeated with the full base setup.

Gemma E4B showed high runtime and memory cost during feasibility checks. The search moved toward Llama, Phi, and Ministral because those models aligned better with the deployment target.

## Final Conclusion

The training and validation search identified two important candidates: Phi-4-mini as the validation leader and Llama 3.2 3B as the stronger practical replacement candidate after final benchmark and deployment evidence were considered.

## Evidence Locations

| Evidence | Path |
|---|---|
| Llama-only optimisation report | `reports/optimization/OPTIMIZATION_REPORT_EN.md` |
| Stage 1 summary | `reports/stage1/stage1_interim_summary_20260512_v2.md` |
| Stage 1 machine summary | `reports/stage1/stage1_anchor_summary.json` |
| Phase2 candidate ranking | `reports/phase2/compressed_candidate_ranking.json` |
| Final selection JSON | `reports/final/compressed_phase2_final_selection_report.json` |
| Evidence allocation matrix | `reports/school_facing/index/EVIDENCE_TO_REPORT_MATRIX.md` |
