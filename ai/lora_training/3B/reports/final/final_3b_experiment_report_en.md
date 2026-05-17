# ClearRead 3B-Scale Model Replacement Experiment Report

Report date: 14 May 2026

## Executive Summary

This experiment investigated whether the ClearRead summarisation system could move from the earlier `Llama 3.1 8B Candidate A` model to a smaller model around the 3B scale while preserving the practical quality needed by the product.

The production task is narrow and repeated: given a source article chunk of roughly 600 words, the model should produce a compact reading-support summary with one `main_idea` and a set of `key_points`. The original benchmark schema required exactly two sentences in `main_idea` and exactly four one-sentence key points. In the current product, however, the frontend can accept a dynamic number of key points, so some strict benchmark failures are less serious for real deployment than they appear in the formal parser.

The previous 8B baseline remained the strongest strict benchmark result:

| System | Frozen benchmark score | Parsed outputs | Severe fails | Notes |
|---|---:|---:|---:|---|
| Old Llama 3.1 8B Candidate A | 78.055556 | 144/145 | 0 | Fixed baseline reused from the previous benchmark |
| Llama 3.2 3B, Phase2 best checkpoint | 75.848485 | 134/145 | 0 | Recommended practical replacement candidate |
| Phi-4-mini, Phase2 best checkpoint | 75.041667 | 136/145 | 1 | Strong validation result, weaker final benchmark reliability |

The final recommendation is to use `Llama 3.2 3B Instruct` with the Phase2 QLoRA adapter `phase2_r32_a64_lr1p5e4_epoch_4` as the best practical 3B replacement candidate. Strict metrics remain slightly below the old 8B model, while content quality is close enough for the current product context. The selected checkpoint has zero severe benchmark failures, avoids the invalid-JSON failure seen in Phi-4-mini, and has a much smaller local GPU memory footprint.

The recommended model is therefore:

| Item | Selected value |
|---|---|
| Base model | `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` |
| Method | SFT + QLoRA |
| Adapter | `phase2_r32_a64_lr1p5e4_epoch_4` |
| LoRA rank / alpha | `r=32`, `alpha=64` |
| Learning rate | `1.5e-4` |
| Selected epoch | 4 |
| Frozen benchmark run | `phase2_llama32_frozen_benchmark_20260514_v1` |

## 1. Project Objective

The ClearRead system is designed to help readers process source text more easily. Its target behaviour is a short, faithful, accessible summary, with long-form essay generation and open-ended answering outside the project scope:

```json
{"main_idea":"Sentence one. Sentence two.","key_points":["Point one.","Point two.","Point three.","Point four."]}
```

The original successful model was based on `Llama 3.1 8B Instruct` with a fine-tuned adapter. It produced strong benchmark results but created a larger deployment footprint. The goal of this experiment was to find whether a smaller 3B-4B model could approach the same quality while using less GPU memory and being easier to deploy.

The experiment covered more than prompt-following behaviour. A model that performs poorly before fine-tuning may still become useful after training if it has good summarisation ability and weak output formatting. For that reason, the work included actual supervised fine-tuning, validation, benchmark scoring, parser analysis, resource checks, and training-data audit.

## 2. Baseline And Evaluation Setup

The old 8B result was kept as a fixed comparison point:

| Baseline | Score | Parsed | Source safety | Main salience |
|---|---:|---:|---:|---:|
| Llama 3.1 8B Candidate A | 78.055556 | 144/145 | 3.354167 | 4.173611 |
| Qwen3-8B prompt-only | 72.853659 | 123/145 | n/a | n/a |
| Llama 3.1 8B base prompt-only | 68.666667 | 18/145 | n/a | n/a |

The final evaluation used the same frozen benchmark prepared inputs from the previous project workflow. These inputs came from the existing test split and were copied into the new experiment workspace to keep previous benchmark artifacts unchanged.

Evaluation had two layers:

1. Structural validation: checks whether the model output can be parsed and follows the expected schema.
2. Accessibility-first judge scoring: scores only parsed outputs for faithfulness, source safety, main message salience, plain language, cognitive-load reduction, sentence accessibility, and scannability.

The most important reported benchmark score is the capped official item score. Safety failures can cap the final score even if the output is otherwise readable.

## 3. Experimental Process

### 3.1 Workspace Isolation

New work was separated from older workspaces. Earlier 8B artifacts were reused only as read-only evidence. In this Git package, the cleaned 3B evidence is placed under:

`ai/lora_training/3B`

The previous 8B package used as the comparison baseline is placed under:

`ai/lora_training/8B`

The experiment preserved raw outputs, parsed outputs, parse failures, judge inputs, judge outputs, score summaries, command logs, exit codes, decision notes, and evidence inventories.

### 3.2 First Direction: Llama 3.2 3B-Specific Optimisation

The first major direction focused only on `Llama 3.2 3B Instruct`. The question was whether a smaller Llama could be tuned close enough to the old 8B model by adjusting training and inference controls.

The starting 3B candidate was weaker than the 8B baseline:

| Experiment | Parsed | Mean score | Notes |
|---|---:|---:|---|
| Original 3B Candidate B epoch 4 | 139/145 | 71.927536 | Initial 3B frozen benchmark |
| r32 epoch 4 + prompt guard v2 | 141/145 | 71.418440 | Better parse, lower score |
| r64 epoch 1 + original prompt | 140/145 | 72.450000 | Improved score, one invalid JSON |
| r64 epoch 1 + prompt guard v2 | 143/145 | 72.118881 | Best parse in this pass |
| r64 epoch 1 + gentle parser guard v3 | 140/145 | 73.835714 | Best score in this pass |

This stage showed that Llama 3.2 3B could improve, but the best result, `73.835714`, still remained below the old 8B baseline of `78.055556`.

The first Llama-only optimisation also tested longer or lower-learning-rate continuation. Those continuation runs completed and gave limited support for replacing the 8B model. The result changed the direction of the project: the search widened from Llama 3.2 3B to other model families.

### 3.3 Training Data Quality Audit

Before expanding the search, the dataset itself was audited. This was important because poor training labels could make all smaller models look worse, regardless of model choice.

A fixed random sample of 100 training pairs was reviewed from the frozen training split of 1162 examples. The review used `gpt-5.5` as the independent reviewer and checked faithfulness, coverage, high-level abstraction, clarity, schema fit, and training value.

| Result | Count |
|---|---:|
| Accept as-is | 90 |
| Minor repair | 10 |
| Rewrite | 0 |
| Drop or manual review | 0 |

Mean scores were high across the review dimensions:

| Dimension | Mean out of 5 |
|---|---:|
| Faithfulness | 4.94 |
| Coverage | 4.89 |
| High-level abstraction | 4.86 |
| Clarity and accessibility | 4.97 |
| Schema/style fit | 5.00 |
| Training value | 4.93 |

The audit concluded that the dataset was generally strong. The few weaknesses were minor and concentrated around long rubrics, health warnings, and some academic detail selection. The next stage therefore focused on model and training choices.

### 3.4 Second Direction: Broader 3B-4B Model Search

The next direction tested a wider group of current 3B-4B candidate models. The main candidates included:

- `unsloth/Llama-3.2-3B-Instruct-bnb-4bit`
- `microsoft/Phi-4-mini-instruct`
- `mistralai/Ministral-3-3B-Instruct-2512-BF16`
- `Qwen/Qwen3.5-4B`
- `ibm-granite/granite-4.1-3b`
- `google/gemma-4-E4B-it`

The broad Stage 1 anchor used a common training setup wherever possible:

| Setting | Value |
|---|---|
| Method | SFT + QLoRA |
| Quantisation | 4-bit NF4 / bf16 where supported |
| LoRA rank | 32 |
| LoRA alpha | 64 |
| Dropout | 0.05 |
| Learning rate | 2e-4 |
| Max sequence length | 3072 |
| Effective batch size | 8 |
| Epochs | 5 |

Each epoch snapshot was validated on the full 145-item validation split, and selected checkpoints were judged on the fixed 50-item validation subset.

The Stage 1 results showed that Phi-4-mini was the strongest validation candidate, while Qwen was slow and Gemma raised deployment concerns:

| Model | Best Stage 1 signal | Best parsed | Training time |
|---|---:|---:|---:|
| Phi-4-mini | 78.54 | 141/145 | 7,217.86 s |
| Qwen3.5-4B | 77.94 | 143/145 | 30,119.68 s |
| Llama 3.2 3B | 75.56 | 140/145 | 11,306.21 s |
| Ministral 3B | 75.94 | 141/145 | 5,987.41 s |
| Granite 4.1 3B | 75.914894 | 141/145 | 7,780.29 s |

These results justified keeping Phi, Llama, and Ministral for deeper local search. Qwen was retained as a quality challenger with limited priority because of its runtime cost. Granite and Gemma moved to evidence-only status.

### 3.5 Deployment Feasibility Checks

A separate local resource probe compared inference time and GPU memory on the same local RTX 4070 Ti SUPER machine. The final model needed both quality and a real deployment advantage over the 8B model.

| Model | Load time | Peak GPU MiB | Mean seconds per block | Parse sanity |
|---|---:|---:|---:|---:|
| Llama 3.1 8B Candidate A | 154.969 s | 7889 | 4.478 | 3/3 |
| Llama 3.2 3B Instruct | 61.857 s | 3688 | 5.284 | 0/3 base prompt-only |
| Ministral 3B | 177.364 s | 4135 | 6.272 | 1/3 |
| Phi-4-mini | 146.952 s | 4547 | 6.990 | 2/3 |
| Qwen3.5-4B | 182.323 s | 5065 | 9.418 | 0/3 |
| Gemma E4B | 310.970 s | 10951 | 15.592 | 3/3 |

This resource check changed the plan. Gemma E4B had promising prompt-only formatting behaviour, yet its measured memory and latency were poorly aligned with the deployment goal. A separate Gemma-vs-8B feasibility check found that the old real Llama 8B vLLM route could process 28 blocks in about 22.7-26.4 seconds on an L4 GPU, while Gemma E4B took about 19.9 seconds for one local block and 37.4 seconds for three local blocks in the tested route. Gemma therefore moved out of the main search path.

### 3.6 Phase2 Compressed Search

The original broad search risked becoming too large. It would have consumed time and judge calls on many combinations that were unlikely to become finalists. The plan was therefore adjusted to a compressed local Phase2 search.

The compressed Phase2 strategy was:

- reuse all existing evidence;
- treat Phi-4-mini as the early validation leader;
- run focused Llama and Ministral challenges;
- use hard kill rules;
- only benchmark the strongest practical finalists;
- stop tuning after the frozen benchmark.

The most important Phase2 validation ranking was:

| Rank | Candidate | Config | Epoch | Val50 score | Parsed | Severe | Major |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | Phi-4-mini | r32 alpha64 lr1.5e-4 | 3 | 80.28 | 140/145 | 0 | 1 |
| 2 | Phi-4-mini | r32 alpha64 lr1e-4 | 4 | 77.306122 | 140/145 | 0 | 4 |
| 3 | Llama 3.2 3B | r32 alpha64 lr1.5e-4 | 4 | 76.46 | 141/145 | 0 | 4 |
| 4 | Phi-4-mini | r32 alpha64 lr1.5e-4 | 4 | 76.285714 | 140/145 | 0 | 2 |
| 7 | Ministral 3B | r32 alpha64 lr1.5e-4 | 4 | 75.28 | 142/145 | 0 | 4 |

Under validation-only selection, Phi-4-mini looked like the best model. However, the frozen benchmark later changed the practical conclusion.

## 4. Final Frozen Benchmark Results

The frozen benchmark is the internal project benchmark from the earlier test workflow. It uses the same frozen prepared inputs copied from the previous benchmark workspace.

### 4.1 Strict Benchmark Results

| System | Score | Parsed | Judge-valid outputs | Before-cap score | Severe | Major |
|---|---:|---:|---:|---:|---:|---:|
| Old Llama 3.1 8B Candidate A | 78.055556 | 144/145 | 144 | 85.965278 | 0 | 5 |
| Llama 3.2 3B Phase2 | 75.848485 | 134/145 | 132 | 82.780303 | 0 | 11 |
| Phi-4-mini Phase2 | 75.041667 | 136/145 | 120 | 83.558333 | 1 | 8 |

The Llama 3.2 3B model scored below the old 8B model by about 2.21 points. However, it outperformed Phi-4-mini in the final frozen benchmark, had no severe failures, and had no invalid JSON failures.

### 4.2 Parse Failure Analysis

Strict parsing matters for formal benchmark reporting, and product behaviour also matters. The current frontend can accept a dynamic number of key points, so a model producing five or seven useful key points can still be usable in the product.

| System | Parse failures | Failure types |
|---|---:|---|
| Llama 3.2 3B Phase2 | 11 | 6 key point one-sentence issues, 2 key point count issues, 3 main-idea sentence-count issues |
| Phi-4-mini Phase2 | 9 | 4 key point one-sentence issues, 4 main-idea sentence-count issues, 1 invalid JSON |

The difference is important. Phi had fewer strict parse failures, but one failure was invalid JSON. Llama's failures were mostly sentence-count or key-point-count strictness issues. In product terms, those are easier to tolerate or handle than completely broken JSON.

### 4.3 Content Comparison Against The 8B Baseline

To understand whether the small model mainly lost points due to formatting or summarisation quality, content fields were compared on overlapping successfully judged items.

For Llama 3.2 3B versus the old 8B model, on 131 common valid input IDs:

| Metric | Average difference, Llama minus 8B |
|---|---:|
| Main message salience | -0.1679 / 5 |
| Source safety margin | -0.1832 / 5 |
| Plain language | -0.1908 / 5 |
| Cognitive-load reduction | -0.1603 / 5 |
| Sentence accessibility | -0.1832 / 5 |
| Scannability | -0.0992 / 5 |

The gap is real and modest. The average difference on the main content fields was around 0.18 on a 0-5 scale. This supports the interpretation that Llama 3.2 3B remains below the old 8B model on strict quality measurement while being close enough to be a practical replacement candidate for this specific product.

For Phi-4-mini versus the old 8B model, on 119 common valid input IDs:

| Metric | Average difference, Phi minus 8B |
|---|---:|
| Main message salience | -0.0924 / 5 |
| Source safety margin | -0.2017 / 5 |
| Plain language | -0.1597 / 5 |
| Cognitive-load reduction | -0.2185 / 5 |
| Sentence accessibility | -0.0840 / 5 |
| Scannability | -0.1176 / 5 |

Phi's content quality was also close, and in some fields slightly closer to 8B than Llama. The final selection favoured Llama because the frozen benchmark exposed Phi reliability concerns: lower capped final score, fewer schema-valid judge outputs, one invalid JSON failure, and one severe failure.

## 5. Final Model Selection

The final selection uses product-aware evidence alongside leaderboard scores.

Phi-4-mini is the strongest validation model. It reached `80.28` on the val50 subset and clearly deserved finalist treatment. However, its frozen benchmark score dropped to `75.041667`, below Llama's `75.848485`. It also had one invalid JSON failure and one severe fail.

Llama 3.2 3B ranked below Phi on the validation subset and became the stronger final replacement candidate because:

- it scored higher than Phi on the frozen benchmark;
- it had zero severe fails;
- it had no invalid JSON failures;
- its strict key-point-count failures are less serious for the current frontend because the frontend accepts a dynamic number of key points;
- it has a lower GPU memory footprint than Phi in the frozen benchmark run;
- it is from the same Llama model family as the previous 8B baseline, which makes the technical transition easier to explain and maintain.

The selected system is:

| Field | Value |
|---|---|
| Final practical choice | Llama 3.2 3B Phase2 |
| System ID | `compressed_final_llama32_3b_instruct_phase2_r32_a64_lr1p5e4_epoch_4` |
| Base model | `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` |
| Adapter | `model_workspaces/llama32_3b_instruct/models/adapters/phase2_r32_a64_lr1p5e4_epoch_4` |
| Training method | SFT + QLoRA |
| Rank / alpha / dropout | `r=32`, `alpha=64`, `dropout=0.05` |
| Learning rate | `1.5e-4` |
| Selected checkpoint | epoch 4 |

## 6. Problems Encountered And Resolutions

The experiment included several engineering problems. The table below keeps those issues visible and records their resolutions.

| Problem | Impact | Resolution |
|---|---|---|
| Llama continuation initially failed due missing gradient checkpointing function | Training continuation stopped before the first training step | A corrected runner restored checkpointing and the run completed |
| A selected r64 adapter directory initially contained only a manifest | Frozen inference stopped during adapter loading | Adapter files were copied into the selected directory and the run was repeated |
| A validation run used a continuation-only config | Validation covered the continuation setup; the intended comparison required the full base setup | The runner was corrected to use the full base config |
| Some helper files were first created in the older training folder because of the default working directory | Risk of workspace confusion | The issue was logged, files were copied to the isolated workspace, and no deletion was performed |
| Gemma E4B training/deployment cost became disproportionate | It could have consumed most of the search budget | The search was paused, a deployment feasibility check was run, and Gemma was removed from the main training path |
| Phase2 ranking script treated `severe_fail_count = 0` incorrectly as an empty value | Valid candidates were filtered incorrectly | The check was corrected to distinguish `0` from missing data |
| The second Phi finalist frozen benchmark hit an artifact/run-id conflict | The run stopped before producing a valid second benchmark result | The issue was recorded; a manual Llama benchmark was run to compare the practical Llama candidate |
| WSL required explicit judge API key forwarding during manual Llama scoring | Judge scoring stopped at environment setup | The API key was passed into WSL through the environment and scoring completed |
| Strict parser rejected useful outputs because of fixed key-point count or sentence-count rules | Some product-usable outputs were counted as strict benchmark failures | The final decision reports strict score and product-aware interpretation separately |

These issues are part of the evidence trail. They explain why the experiment changed direction twice: first from Llama-only optimisation to broader model search, and then from broad exhaustive search to compressed local finalist selection.

## 7. Limitations

This conclusion is specific to the ClearRead task, dataset, benchmark, and product frontend. It is a practical replacement decision for this product setting.

Main limitations:

- The frozen benchmark uses pre-split text chunks from the existing project workflow.
- The old 8B baseline numbers were reused from the earlier fixed benchmark.
- Judge scoring is computed only for outputs that pass the benchmark parser.
- The benchmark is an accessibility-first engineering benchmark; clinical validation remains outside scope.
- Local sequential inference differs from a production vLLM deployment route.
- Some strict parse failures remain product-usable because the frontend accepts dynamic key-point counts.
- The final recommendation is a practical engineering decision for the completed search budget.

## 8. Conclusion

The experiment supports replacing the old 8B model with the selected `Llama 3.2 3B Instruct` fine-tuned checkpoint for the current ClearRead product context.

The old 8B model remains better on strict benchmark score and parser stability. However, the selected 3B model reduces GPU memory needs, has no severe failures, avoids invalid JSON, and shows only a modest content-quality gap compared with the 8B model. Since the product can handle a variable number of key points, the most visible Llama parse issue is less serious in deployment than in the strict benchmark.

The final answer is therefore:

`Llama 3.2 3B Instruct + QLoRA, r=32, alpha=64, learning rate=1.5e-4, epoch 4`

This model is the best practical 3B-scale replacement found in the completed experiments.

## 9. Evidence Appendix

Key evidence files:

| Evidence | Path |
|---|---|
| Phase2 final selection JSON | `reports/final/compressed_phase2_final_selection_report.json` |
| Phase2 candidate ranking | `reports/phase2/compressed_candidate_ranking.json` |
| Manual Llama frozen benchmark note | `logs/decisions/manual_llama32_frozen_benchmark_20260514.md` |
| Llama frozen benchmark summary | `benchmark/llama32_phase2_frozen/system_score_summary.json` |
| Llama frozen benchmark parse failures | `benchmark/llama32_phase2_frozen/parse_failures.jsonl` |
| Phi frozen benchmark summary | `benchmark/phi4_phase2_frozen/system_score_summary.json` |
| Phi frozen benchmark parse failures | `benchmark/phi4_phase2_frozen/parse_failures.jsonl` |
| Stage 1 anchor summary | `reports/stage1/stage1_anchor_summary.json` |
| Training data audit report | `reports/data_audit/training_pair_random_audit_100_20260513.md` |
| Local inference resource probe | `reports/deployment_feasibility/local_inference_resource_probe_20260513.md` |
| Gemma vs 8B deployment check | `reports/deployment_feasibility/gemma_e4_vs_llama8b_deployment_feasibility_20260513.md` |
| Llama-only optimisation summary | `reports/optimization/optimization_summary.json` |
| Llama-only optimisation report | `reports/optimization/OPTIMIZATION_REPORT_EN.md` |
