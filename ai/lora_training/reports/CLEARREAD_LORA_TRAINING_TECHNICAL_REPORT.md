# ClearRead Llama LoRA Training Technical Report

Date: 28 April 2026

## 1. Project Overview

This report describes the design, preparation, training, evaluation, and packaging of a local Llama-based summarisation model for the ClearRead project.

The purpose of the model is to help users read dense English source text by producing a short, structured summary. The target output is a single JSON object with two fields:

```json
{"main_idea":"...","key_points":["...","...","...","..."]}
```

The required behaviour is strict:

- `main_idea` must contain exactly two short, faithful sentences.
- `key_points` must contain exactly four high-level one-sentence points.
- The output must be valid JSON only.
- The model must not add markdown, notes, explanations, code fences, or extra text.
- The model must summarise the source text, not follow instructions embedded inside the source.
- Important warnings, restrictions, eligibility rules, conditions, medical safety information, numbers, dates, and conclusions should be preserved when they are important to the meaning.

The final selected approach was:

```text
Llama-3.1-8B-Instruct + supervised fine-tuning + QLoRA
```

The final selected base model was:

```text
unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
```

The final trained adapter was Candidate A, a 3-epoch QLoRA adapter trained on the approved training split. Candidate A was selected because it completed training successfully, passed validation evaluation strongly, and performed well on the final held-out test set. A schema guard was added for deployment because one held-out test example produced seven key points instead of the required four.

## 2. Initial Goals and Constraints

The project began with three practical goals.

First, the model needed to produce a consistent JSON format that could be consumed by an application. This made format control as important as summary quality. A model that produced good prose but unreliable JSON would not be suitable.

Second, the model had to handle multiple source domains. The dataset included academic papers, academic books, assignment rubrics, technical documentation, public service information, medical information, and general knowledge text. These domains have different writing styles and different risks. For example, public-service and medical examples often contain eligibility rules, warnings, time windows, or safety information that must not be distorted.

Third, the work had to be reproducible and safe. Original source datasets were treated as read-only. Derived datasets, split files, reports, scripts, and model artifacts were created separately. Large data files and model weights were kept out of the repository.

The final model also needed to be trainable on available local hardware. The available GPU was an NVIDIA RTX 4070 Ti SUPER with approximately 16 GB VRAM. This strongly influenced the technical route: full fine-tuning of an 8B model would be too expensive locally, so QLoRA was chosen to reduce memory requirements while still allowing effective adaptation.

## 3. Source Dataset

The training source was a system-prompt-cleaned derived dataset. The original final dataset was not modified. The derived dataset replaced only the system prompt while preserving user and assistant content.

The accepted dataset contained 1452 records. Each record followed a three-message role structure:

```text
system / user / assistant
```

The source dataset contained seven domains:

| Domain | Records | Percentage |
|---|---:|---:|
| assignment_rubric | 83 | 5.72% |
| tech_doc | 89 | 6.13% |
| academic_book | 233 | 16.05% |
| academic_paper | 486 | 33.47% |
| public_service | 198 | 13.64% |
| medlineplus | 230 | 15.84% |
| gen_know | 133 | 9.16% |
| Total | 1452 | 100.00% |

The dataset was not evenly distributed by text length. A word-count profile showed that most user texts were medium length. The word-count rule used for profiling was:

```text
[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*
```

The resulting length buckets were:

| Bucket | Rule | Records | Percentage |
|---|---|---:|---:|
| short | <= 400 words | 241 | 16.60% |
| medium | 401-800 words | 1018 | 70.11% |
| long | >= 801 words | 193 | 13.29% |

This distribution influenced the split strategy. Instead of forcing equal numbers of short, medium, and long examples, the split preserved the real distribution as closely as possible.

## 4. Data Splitting Method

The dataset was split into train, validation, and test sets using an 80/10/10 design:

| Split | Records | Percentage |
|---|---:|---:|
| train | 1162 | 80.03% |
| validation | 145 | 9.99% |
| test | 145 | 9.99% |

The split was designed to preserve both domain distribution and length distribution. The method used deterministic approximate joint stratification over:

```text
domain x natural_length_bucket
```

The split first matched the target number of records for each domain. Then, within each domain, it preserved that domain's own short, medium, and long distribution as closely as integer counts allowed.

The final per-domain split was:

| Domain | Total | Train | Validation | Test |
|---|---:|---:|---:|---:|
| assignment_rubric | 83 | 67 | 8 | 8 |
| tech_doc | 89 | 71 | 9 | 9 |
| academic_book | 233 | 187 | 23 | 23 |
| academic_paper | 486 | 388 | 49 | 49 |
| public_service | 198 | 158 | 20 | 20 |
| medlineplus | 230 | 184 | 23 | 23 |
| gen_know | 133 | 107 | 13 | 13 |
| Total | 1452 | 1162 | 145 | 145 |

The final overall length-bucket distribution was:

| Bucket | Source | Train | Validation | Test |
|---|---:|---:|---:|---:|
| short | 241 | 191 | 25 | 25 |
| medium | 1018 | 816 | 101 | 101 |
| long | 193 | 155 | 19 | 19 |

A 10-record smoke set was also created from the training split only. It covered multiple domains and length buckets and was used for low-risk environment and training checks before full training.

The split was verified with several checks:

- Train, validation, and test counts matched the target counts.
- No record appeared in more than one of train, validation, and test.
- All 1452 source records were accounted for.
- Domain targets were matched exactly.
- The split manifest contained metadata only and did not contain raw message text.
- Re-running the split script produced identical output hashes.
- Source file hashes were unchanged after split generation.

## 5. Teammate Export Preparation

After the split, a simple teammate-facing export was created. The purpose was to separate user and assistant content into aligned files while preserving stable metadata. This allowed another team member to use the data without requiring the full chat-message format.

The export created user-only and assistant-only files for train, validation, test, and all records:

| Scope | User Rows | Assistant Rows |
|---|---:|---:|
| train | 1162 | 1162 |
| validation | 145 | 145 |
| test | 145 | 145 |
| all | 1452 | 1452 |

The export was verified row by row. User and assistant records matched on pair index, pair id, record id, stable hash, split, domain, source file, source line, and length bucket. The export did not include the system prompt or full `messages` field. Source split hashes remained unchanged.

These export files were kept as derived local data and were not included in this package.

## 6. Training Environment

Training was carried out in a clean WSL2 Ubuntu conda environment. The environment was created specifically for this Llama-3.1-8B QLoRA training route.

Important environment details:

| Item | Value |
|---|---|
| Operating environment | Ubuntu on WSL2 |
| Python | 3.11.15 |
| GPU | NVIDIA GeForce RTX 4070 Ti SUPER |
| VRAM | approximately 16 GB |
| PyTorch | 2.10.0+cu128 |
| CUDA runtime | 12.8 |
| BF16 support | available |
| CUDA availability | verified |

Important package versions:

| Package | Version |
|---|---:|
| torch | 2.10.0 |
| transformers | 5.5.0 |
| datasets | 4.3.0 |
| accelerate | 1.13.0 |
| peft | 0.19.1 |
| trl | 0.24.0 |
| bitsandbytes | 0.49.2 |
| unsloth | 2026.4.8 |
| huggingface_hub | 1.12.0 |
| safetensors | 0.7.0 |
| sentencepiece | 0.2.1 |
| xformers | 0.0.35 |

Several issues appeared during environment setup:

| Issue | Impact | Resolution |
|---|---|---|
| Hugging Face CLI was not logged in | Official gated Meta model could not be used directly | The public Unsloth 4-bit model was used as the preferred model; the official Meta model remained a fallback requiring future authentication |
| Flash Attention 2 was not working | Potential performance optimisation was unavailable | Unsloth fell back to xformers; CUDA, BF16, and import tests passed, so this was accepted |
| Unsloth dependency resolution selected a newer torch/CUDA stack | Could have caused compatibility problems | The resolved stack was kept after runtime CUDA tensor tests and package imports passed |

The environment was considered ready after GPU visibility, CUDA tensor execution, BF16 support, and core package imports all passed.

## 7. Model and Training Strategy

The selected model family was Llama 3.1 8B Instruct. The instruct variant was used because the task is a structured instruction-following summarisation task, not general language modelling.

QLoRA was selected for local training because it allows fine-tuning a large model with much lower GPU memory usage. This was important because the available GPU had approximately 16 GB VRAM. The model was loaded in 4-bit form, and LoRA adapters were trained on top of the base model.

The core training strategy was supervised fine-tuning. The assistant JSON response was the target output. System and user/source tokens were masked from the loss so that the model learned only to produce the assistant JSON completion.

The main LoRA configuration used for full training was:

| Setting | Value |
|---|---|
| LoRA rank | 16 |
| LoRA alpha | 32 |
| LoRA dropout | 0.05 |
| Target modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Quantisation | 4-bit NF4 |
| Max sequence length | 3072 |
| Training method | SFT |
| Tuning method | QLoRA |
| Optimiser | adamw_8bit |
| Learning rate | 0.0002 |
| Epochs | 3 |
| Effective batch size | 8 |
| Seed | 5120 |

The max sequence length of 3072 was chosen after profiling showed that all examples fit safely under this limit. Full training preflight later confirmed zero truncation for both train and validation records.

## 8. Assistant-Only Loss Masking

A key technical risk was accidentally training the model to reproduce the prompt or user/source text. To prevent this, explicit assistant-only label masking was implemented.

The training data utility rendered each example twice using the tokenizer chat template:

1. system + user with an assistant generation prompt;
2. system + user + assistant full text.

The prompt prefix tokens were masked with `-100`, so they did not contribute to loss. Only the assistant JSON completion tokens remained trainable.

The label-mask sanity check on the 10-record smoke set produced:

| Check | Result |
|---|---:|
| Smoke records checked | 10 |
| Records with trainable assistant tokens | 10 |
| Decoded trainable labels parse as JSON | 10 |
| Decoded trainable JSON matches source assistant JSON | 10 |
| Total masked prompt tokens | 12071 |
| Total trainable assistant tokens | 1323 |
| Truncated records | 0 |

This confirmed that training loss was applied only to the desired assistant JSON outputs.

## 9. Smoke Training

Before full training, a small smoke training run was performed on the 10-record smoke set. This was used to verify that the environment, tokenizer, label masking, QLoRA setup, adapter saving, and inference flow worked end to end.

Smoke training result:

| Item | Value |
|---|---|
| Status | success |
| OOM | no |
| Steps | 20 |
| Final training loss | 0.5587 |
| Final step loss | 0.02816 |
| Trainer runtime | 87.37 seconds |
| Script elapsed time | 89.61 seconds |
| Final average speed | 4.368 seconds/step |

The smoke adapter was then used for inference sanity checks:

| Check | Result |
|---|---:|
| Examples checked | 3 |
| Valid JSON schema | 3/3 |
| Required keys present | 3/3 |

One operational issue occurred: an initial attempt to launch training from PowerShell as a background WSL process failed because command quoting broke before conda activation. No training or adapter write occurred in that failed attempt. The command was then run directly in WSL and succeeded.

The successful smoke run justified moving to full training.

## 10. Candidate A Full Training

Candidate A was the first full training run. It used the approved train and validation splits.

Preflight checks confirmed that the configured sequence length was sufficient:

| Split | Records | Max Input Tokens | Max Assistant Tokens | Total Assistant Tokens | Truncated Records |
|---|---:|---:|---:|---:|---:|
| train | 1162 | 2296 | 192 | 148979 | 0 |
| validation | 145 | 2171 | 204 | 18677 | 0 |

Full training result:

| Item | Value |
|---|---|
| Status | success |
| OOM | no |
| Epochs | 3 |
| Optimiser steps | 438 |
| Final train loss | 0.4797596574748216 |
| Validation loss | 0.9654271602630615 |
| Training time | 1h 04m 39s |
| Final ETA callback speed | 8.68 seconds/step |

After training, inference was run on validation examples:

| Check | Result |
|---|---:|
| Validation examples checked | 10 |
| Schema pass | 10/10 |

One minor preflight issue was found: two training records had decoded-label exact JSON object mismatches caused by tokenizer decode spacing around `.gov`. These labels still parsed as JSON, were non-empty, and had no truncation. Therefore, the issue was recorded but not treated as a blocker.

Candidate A was considered viable for broader validation quality auditing.

## 11. Validation Quality Audit

Candidate A was evaluated on the full validation split. The test set was not used at this stage.

Validation generation summary:

| Item | Value |
|---|---|
| Validation records | 145 |
| Runtime | 11m 38s |
| Average speed | 4.814 seconds/example |

Validation deterministic metrics:

| Metric | Result |
|---|---:|
| JSON parse | 145/145 |
| Schema pass | 145/145 |
| Exact key order | 145/145 |
| Exactly 4 key points | 145/145 |
| Main idea two-sentence heuristic | 144/145 |
| Each key point one-sentence heuristic | 143/145 |
| Markdown/code-fence leakage | 0 |
| Extra text outside JSON | 0 |
| Refusal/meta-response phrases | 0 |
| Prediction mojibake rows | 0 |
| Gold mojibake rows | 0 |

Manual review covered 16 validation examples across domains and length buckets:

| Manual Label | Count |
|---|---:|
| pass | 14 |
| minor_issue | 2 |
| major_issue | 0 |
| uncertain | 0 |

The validation review found no instruction-following failures, no refusal or meta-response behaviour, no encoding collapse, and no broad domain or length-bucket quality collapse. The two minor issues were isolated precision or wording issues.

An apparent mojibake issue was investigated during validation review. It was determined to be a terminal/display artifact rather than actual corruption in the data or prediction files.

Based on validation evidence, Candidate A was approved for final held-out test evaluation. Candidate B was not recommended.

## 12. Final Held-Out Test Evaluation

The final test evaluation was performed only after Candidate A was selected from validation evidence. The test set was used once for final evaluation, not for training or hyperparameter tuning.

Test generation summary:

| Item | Value |
|---|---|
| Test records | 145 |
| Runtime | 11m 50s |
| Average speed | 4.899 seconds/example |

Final test deterministic metrics:

| Metric | Result |
|---|---:|
| JSON parse | 145/145 |
| Schema pass | 144/145 |
| Exact key order | 145/145 |
| Main idea string | 145/145 |
| Key points list | 145/145 |
| Exactly 4 key points | 144/145 |
| All key points strings | 145/145 |
| Main idea two-sentence heuristic | 144/145 |
| Each key point one-sentence heuristic | 144/145 |
| Empty-string rows | 0 |
| Output too short / too long | 0 / 0 |
| Markdown/code-fence leakage | 0 |
| Extra text outside JSON | 0 |
| Refusal/meta-response phrases | 0 |
| Prediction mojibake rows | 0 |
| Gold mojibake rows | 0 |

Manual review covered 17 final test examples:

| Manual Label | Count |
|---|---:|
| pass | 14 |
| minor_issue | 2 |
| major_issue | 1 |
| uncertain | 0 |

The only major issue was a schema-contract failure on one academic paper example. The output was parseable and broadly faithful, but it contained seven key points instead of exactly four. This reduced raw schema compliance to 144/145.

One sentence-count heuristic failure was also reviewed and found to be a false positive caused by punctuation in `E. coli`. The output itself was valid and faithful.

The final test did not reveal broad domain failure, medical safety reversal, public-service instruction failure, refusal behaviour, markdown leakage, extra text, or encoding collapse.

## 13. Final Model Selection

Candidate A was selected as the final raw adapter for this training cycle.

The reasons were:

- It completed full 3-epoch training without OOM.
- It had zero truncation in train and validation preflight checks.
- It passed validation schema checks on 145/145 validation records.
- Validation manual review found no major issues.
- Final test JSON parsing was 145/145.
- Final test raw schema compliance was 144/145.
- The only schema failure was isolated and fixable at deployment with a schema guard.
- There was no evidence of broad domain, length, safety, or instruction-following collapse.

Candidate B was not trained. After the held-out test result was known, training a new candidate to address the one schema miss would have used test feedback for model selection and would have contaminated the final evaluation.

## 14. Deployment Schema Guard

Because the raw model produced one held-out output with seven key points, a schema guard was implemented for local inference.

The guard checks:

- JSON is parseable.
- Keys are exactly `main_idea` followed by `key_points`.
- `main_idea` is a string.
- `key_points` is a list of strings.
- There are exactly four final key points.

Guard policy:

| Raw Output Condition | Guard Action |
|---|---|
| Valid JSON with exactly four key points | Return final JSON |
| Valid JSON with more than four key points | Return the first four generated key points and record `truncated_key_points` in debug output |
| Too few key points | Return a machine-readable error object |
| Invalid JSON | Return a machine-readable error object |
| Wrong keys, key order, or value types | Return a machine-readable error object |

This guard is a deployment safety layer. It does not change the final held-out test score.

## 15. Final Inference Interface

The final local inference wrapper supports:

- direct text input;
- file input;
- stdin input;
- JSONL smoke or validation input for sanity checks.

It imports Unsloth before PEFT-related imports, loads the selected base model and adapter, applies the same system prompt used in training, generates deterministically by default, and validates the output before returning it.

Default successful output is only the final JSON object. Debug mode can show raw output, guarded output, status, schema guard action, and schema errors.

## 16. Reproducibility and Artifact Management

The project kept a clear separation between process records and large or sensitive artifacts.

This package includes:

- scripts;
- configs;
- documentation;
- reports;
- decision logs;
- small metadata files.

Large artifacts are represented by metadata rather than stored directly:

- full train/validation/test JSONL files;
- teammate export JSONL files;
- validation/test prediction JSONL files;
- adapter `.safetensors`;
- base model weights;
- checkpoints;
- optimiser states;
- Hugging Face cache files;
- Unsloth cache files;
- `.pt`, `.pth`, and `.bin` files.

This separation keeps the workflow reproducible while avoiding large model artifacts and raw datasets in the submitted package.

## 17. Main Problems and Solutions

| Problem | Why It Mattered | Solution |
|---|---|---|
| Length buckets could have been split artificially evenly | This would not reflect the real dataset | The split preserved real domain and length distributions using domain x length stratification |
| Original data could be accidentally changed | This would damage reproducibility | Source datasets were treated as read-only, and all outputs were derived separately |
| Local GPU memory was limited | Full fine-tuning an 8B model would be difficult | QLoRA with a 4-bit base model was used |
| Hugging Face authentication was unavailable | Official Meta fallback could not be downloaded directly | Public Unsloth 4-bit model was used as the primary model |
| Flash Attention 2 was unavailable | Could affect performance | xformers fallback was accepted after runtime checks passed |
| PowerShell-to-WSL background launch failed | Could interrupt training automation | Training was run directly in WSL |
| Tokenizer spacing caused minor decoded-label mismatch | Could look like label corruption | JSON parse and non-empty labels were verified; no truncation occurred |
| A display looked like mojibake | Could suggest encoding corruption | Files were checked with UTF-8 parsing; it was only a display artifact |
| `E. coli` triggered a sentence-count false positive | Heuristic evaluation could overstate an error | Manual review confirmed the output was valid |
| One held-out output had seven key points | Raw schema compliance was not perfect | A schema guard was implemented for deployment |
| Tuning after seeing test results would contaminate evaluation | It would make held-out results unreliable | Candidate B was skipped after test evaluation |

## 18. Key Findings and Reflections

The most important finding was that format reliability must be treated as a first-class requirement. The model produced strong summaries and valid JSON in nearly all cases, but one held-out failure still mattered because the application expects exactly four key points. This led to the schema guard decision.

A second finding was that preserving the dataset's real distribution was important. The dataset was naturally dominated by medium-length texts, and forcing equal short/medium/long splits would have produced unrealistic validation and test sets. The final split better represented the actual data.

A third finding was that validation quality was strong enough to avoid unnecessary additional training. Training Candidate B might have been possible, but the evidence did not justify it before the test set was used. After the test set was used, training a new candidate based on that result would have weakened the evaluation methodology.

A fourth finding was that local training was feasible on the available hardware with QLoRA. The 8B instruct model could be trained locally without OOM, and a 3-epoch run completed in about one hour.

Finally, evaluation needed both deterministic metrics and manual review. Deterministic checks were excellent for JSON validity, key order, key count, and leakage detection. Manual review was still needed to identify false positives, such as the `E. coli` sentence-count issue, and to judge summary faithfulness.

## 19. Final Outcome

The training phase produced a usable local summarisation model adapter and a safe inference wrapper.

Final selected model:

```text
Llama-3.1-8B-Instruct + SFT + QLoRA
```

Base model:

```text
unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
```

Training outcome:

| Item | Result |
|---|---|
| Full training | completed |
| OOM | no |
| Epochs | 3 |
| Optimiser steps | 438 |
| Final train loss | 0.4797596574748216 |
| Validation loss | 0.9654271602630615 |
| Validation schema pass | 145/145 |
| Final test JSON parse | 145/145 |
| Final test raw schema pass | 144/145 |
| Final decision | Candidate A selected |

The final model should be used with the implemented schema guard. The next stage should focus on application integration, user-facing handling of wrapper errors, and long-term backup for the external model artifacts.

## 20. Future Work

Recommended next steps are:

1. Integrate the inference wrapper into the ClearRead application backend.
2. Define how the application should handle machine-readable schema guard errors.
3. Add controlled retry logic only if it can be evaluated without contaminating held-out results.
4. Preserve the final adapter in a reliable storage location outside this repository.
5. Continue monitoring public-service numeric details, medical safety wording, and exact output shape during application testing.
