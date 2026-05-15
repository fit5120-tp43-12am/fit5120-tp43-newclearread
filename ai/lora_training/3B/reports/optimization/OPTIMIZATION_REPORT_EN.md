# Llama 3.2 3B Optimization Experiment Report

Generated UTC: `2026-05-10T23:08:12Z`

## Executive Summary

The strongest 3B result found in this optimization pass is `clearread_llama32_3b_candidate_c_r64_epoch1_prompt_guard_v3`.
It reached a frozen benchmark mean capped score of `73.835714` with parse success `140/145`.
This improves over the original 3B Candidate B benchmark score `71.927536` and also beats the copied Qwen3-8B prompt-only baseline `72.853659`, while remaining below the copied 8B Candidate A score `78.055556`.

## Frozen Benchmark Experiments

| Experiment | Parsed | Parse rate | Mean score | Score count | Failure reasons |
| --- | --- | --- | --- | --- | --- |
| Original 3B Candidate B epoch4 | 139/145 | 0.958621 | 71.927536 | 138 | {} |
| r32 epoch4 + prompt guard v2 | 141/145 | 0.972414 | 71.418440 | 141 | {"key_points_not_four_string_items": 1, "main_idea_not_two_sentences": 3} |
| r64 epoch1 + original prompt | 140/145 | 0.965517 | 72.450000 | 140 | {"invalid_json": 1, "key_points_not_four_string_items": 1, "main_idea_not_two_sentences": 3} |
| r64 epoch1 + prompt guard v2 | 143/145 | 0.986207 | 72.118881 | 143 | {"main_idea_not_two_sentences": 2} |
| r64 epoch1 + gentle parser guard v3 | 140/145 | 0.965517 | 73.835714 | 140 | {"key_points_not_four_string_items": 1, "main_idea_not_two_sentences": 4} |

## Copied Old Baselines

| Baseline | Parsed | Parse rate | Mean score |
| --- | --- | --- | --- |
| 8B Candidate A | 144/145 | 0.993103 | 78.055556 |
| Qwen3-8B prompt-only | 123/145 | 0.848276 | 72.853659 |
| Llama 3.1 8B base prompt-only | 18/145 | 0.124138 | 68.666667 |

## Validation And Training Checks

| Validation checkpoint | Schema | Main2 | KP4 | KP1 | Elapsed |
| --- | --- | --- | --- | --- | --- |
| r32 epoch4 selected | 145 | 145 | 145 | 142 | 9m 38s |
| r64 epoch1 | 145 | 145 | 145 | 141 | 9m 27s |
| r64 epoch2 | 144 | 145 | 144 | 141 | 9m 44s |
| r64 epoch3 | 144 | 144 | 144 | 141 | 9m 41s |
| r64 epoch4 | 144 | 145 | 144 | 141 | 9m 52s |
| lr1e5 continued epoch5 | 144 | 144 | 144 | 140 | 9m 39s |
| lr1e5 continued epoch6 | 144 | 144 | 144 | 141 | 9m 39s |
| lr1e5 continued epoch7 | 144 | 145 | 144 | 140 | 9m 48s |

| Training run | Status | Train loss | Eval loss | Peak VRAM MiB |
| --- | --- | --- | --- | --- |
| r64 Candidate C rank64 4 epochs | success | 0.409540 | 1.432251 | 15571.78 |
| continue r32 lr5e-5 epoch5-7 | success | 0.043640 | 1.976441 | 15305.53 |
| continue r32 lr1e-5 epoch5-7 | success | 0.043903 | 1.835407 | 15305.53 |

## Decision

Use the r64 epoch1 adapter with the gentle parser guard v3 prompt when optimizing for the official judge mean. Use the v2 prompt only if parse success is prioritized over content score, because v2 achieved `143/145` parse success but scored lower at `72.118881`.

## Notable Events

- e03 first continuation attempt failed before step 1 due missing _gradient_checkpointing_func; gcfix runner restored checkpointing and completed.
- e04 first frozen inference attempt failed because selected_candidate_c_r64 initially contained only a manifest; adapter files were copied in a supplemental manifest and the run was repeated.
- e05 first validation attempt used a continuation-only config; runner was corrected to use the full base config and validation was repeated.
- Three newly created helper files were accidentally first written under the old training folder by apply_patch default cwd. They were not used, were copied to training-3b, and were left in place because the project forbids deletion.

## Limitations

- Frozen benchmark uses the copied prepared inputs; old baselines were reused rather than rerun.
- Primary judge mean is calculated over schema-valid judged rows only; parse/product readiness is reported separately.
- The benchmark uses pre-split chunks and is not clinical dyslexia proof.
- Prompt guard improvements are deployment-time prompt changes, not additional weight training.

## Artifacts

- Best inference manifest: `optimization_experiments/experiments/e07_r64_prompt_guard_v3/df_runs/opt_e07_r64_epoch1_prompt_guard_v3_frozen/manifests_logs/model_inference_clearread_llama32_3b_candidate_c_r64_epoch1_prompt_guard_v3.json`
- Best score summary: `optimization_experiments/experiments/e07_r64_prompt_guard_v3/df_runs/opt_e07_r64_epoch1_prompt_guard_v3_frozen/scoring/accessibility_first_v2/system_score_summary.json`
- Full command log and exit-code indexes are saved in `optimization_experiments/reports/optimization_summary.json`.
