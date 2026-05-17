# Training Data Quality Audit for Small-Model Fine-Tuning

## Executive Summary

This report documents a quality audit of the supervised fine-tuning dataset used for the ClearRead summarization model. The project originally used a larger Llama 3.1 8B instruction-tuned model with LoRA fine-tuning. The next development phase aims to reduce deployment cost by moving toward a smaller model in the 3B to 4B range while preserving the same output format and a comparable level of summarization quality.

Before this audit, several model-side improvement directions were explored, including changes to training epochs, LoRA rank, learning rate, checkpoint selection, and inference prompt guards. These experiments improved understanding of the smaller-model search space, but the observed quality did not consistently reach the expected level compared with the earlier 8B baseline. This raised an important methodological question: whether the limitation came mainly from the smaller model and training setup, or whether the training targets themselves were not strong enough to teach high-level summarization.

To investigate that question, a fixed random sample of 100 training pairs was independently reviewed. The audit found that the dataset is generally strong: 90 of 100 sampled pairs were accepted as-is, 10 were marked for minor repair, and none were marked for rewrite or removal. The evidence does not support a large-scale relabeling effort before the next fine-tuning stage. Instead, the current dataset can remain the baseline for continued small-model training and parameter search.

## Project Context

The target product behavior is a compact structured summary for reading support. Given a source text of approximately 600 words, the model should return one JSON object:

```json
{"main_idea":"two short faithful sentences","key_points":["...","...","...","..."]}
```

The first implemented candidate used a Llama 3.1 8B instruction model with LoRA fine-tuning. Although that model provided a strong quality baseline, it also created a larger deployment footprint. The current work therefore investigates whether a smaller model, especially around the 3B scale, can provide a better practical balance between output quality, inference speed, and GPU memory usage.

The smaller-model investigation has so far included both deployment feasibility checks and training experiments. The main candidates retained for deeper work are Llama 3.2 3B Instruct, Ministral 3B, and Phi-4-mini. Earlier parameter explorations suggested that smaller models are sensitive to training setup, especially epoch count, LoRA rank, and learning rate. However, because parameter changes alone did not fully explain the quality gap, the dataset itself was audited before committing to a larger hyperparameter sweep.

## Audit Objective

The audit evaluates whether the existing supervised fine-tuning target outputs are suitable for teaching a smaller model to produce faithful, high-level, accessible summaries. It focuses on the quality of the training labels, not on model outputs.

The audit answers three questions:

1. Are the target summaries faithful to the source texts?
2. Are the summaries high-level enough for the intended two-sentence summary and four-key-point format?
3. Is there evidence that the dataset needs broad relabeling before further 3B-scale model training?

## Method

The audit used the frozen training split that had already been separated from validation and test data. No training examples were edited during this audit.

| Item | Value |
|---|---|
| Sample frame | Frozen training split only |
| Training split size | 1162 pairs |
| Sample size | 100 pairs |
| Sampling method | Fixed-seed simple random sample without replacement |
| Random seed | 20260513 |
| Reviewer model | gpt-5.5 |
| Review schema | training_pair_quality_audit_v1 |
| Training data modified | No |

Each sampled source-target pair was judged on six dimensions:

- faithfulness to the source text;
- coverage of the main message;
- high-level abstraction rather than detail copying;
- clarity and accessibility of language;
- fit with the required JSON style and schema;
- usefulness as a fine-tuning example.

The reviewer assigned one of four final decisions:

- `accept`: keep as-is.
- `minor_repair`: mostly good, but would benefit from small cleanup.
- `rewrite`: usable source text, but target label should be regenerated or substantially revised.
- `drop_or_manual_review`: possible severe problem; do not use automatically without human review.

## Dataset Coverage

### Sample By Source Domain

| Category | Count | Share |
|---|---:|---:|
| academic_paper | 35 | 35.0% |
| medlineplus | 16 | 16.0% |
| academic_book | 14 | 14.0% |
| gen_know | 13 | 13.0% |
| public_service | 12 | 12.0% |
| tech_doc | 8 | 8.0% |
| assignment_rubric | 2 | 2.0% |

### Sample By Length Bucket

| Category | Count | Share |
|---|---:|---:|
| medium | 75 | 75.0% |
| short | 13 | 13.0% |
| long | 12 | 12.0% |

## Audit Results

Out of `100` successfully audited training pairs:

- `90` were accepted as-is.
- `10` were marked for minor repair.
- `0` were marked for rewrite.
- `0` were marked for drop or manual review.

This means `100` / `100` pairs were judged broadly usable with no or minor changes, while `0` / `100` pairs needed substantial attention before they could be trusted as training labels.

### Decision Counts

| Category | Count | Share |
|---|---:|---:|
| accept | 90 | 90.0% |
| minor_repair | 10 | 10.0% |

### Severity Counts

| Category | Count | Share |
|---|---:|---:|
| none | 90 | 90.0% |
| minor | 10 | 10.0% |

### Mean API Scores

| Score dimension | Mean out of 5 |
|---|---:|
| faithfulness | 4.94 |
| coverage | 4.89 |
| high level abstraction | 4.86 |
| clarity accessibility | 4.97 |
| schema style fit | 5 |
| training value | 4.93 |

## Issue Analysis

### Issue Tag Counts

| Category | Count | Share |
|---|---:|---:|
| critical_omission | 4 | 30.8% |
| requirement_or_constraint_loss | 3 | 23.1% |
| unsupported_fact | 2 | 15.4% |
| medical_or_safety_nuance_loss | 2 | 15.4% |
| too_detailed | 1 | 7.7% |
| source_instruction_following_risk | 1 | 7.7% |

## Results By Domain

### Domain-Level Results

| Group | n | Accept | Minor repair | Rewrite | Manual/drop | Mean training value |
|---|---:|---:|---:|---:|---:|---:|
| academic_book | 14 | 13 | 1 | 0 | 0 | 5 |
| academic_paper | 35 | 33 | 2 | 0 | 0 | 4.943 |
| assignment_rubric | 2 | 1 | 1 | 0 | 0 | 4.5 |
| gen_know | 13 | 11 | 2 | 0 | 0 | 4.923 |
| medlineplus | 16 | 14 | 2 | 0 | 0 | 4.875 |
| public_service | 12 | 11 | 1 | 0 | 0 | 5 |
| tech_doc | 8 | 7 | 1 | 0 | 0 | 4.875 |

## Results By Length Bucket

### Length-Level Results

| Group | n | Accept | Minor repair | Rewrite | Manual/drop | Mean training value |
|---|---:|---:|---:|---:|---:|---:|
| long | 12 | 9 | 3 | 0 | 0 | 4.833 |
| medium | 75 | 68 | 7 | 0 | 0 | 4.933 |
| short | 13 | 13 | 0 | 0 | 0 | 5 |

## Structural Checks

Before API review, each target was checked locally for parseability, key order, sentence count, key-point count, one-sentence key points, and markdown fences. These checks are weaker than semantic review, but they identify labels that may teach unstable output formatting.

Structure failure counts in the sampled set:

### Local Structure Failure Counts

| Category | Count | Share |
|---|---:|---:|
| key_points_one_sentence_each | 1 | 100.0% |

## Highest-Risk Sample Examples

The table below lists the highest-risk examples by severity and training-value score. The report does not include full source text; raw audit artifacts are stored separately for traceability.

| Sample ID | Record ID | Domain | Length | Decision | Severity | Training value | Issue tags | Rationale |
|---|---|---|---|---|---|---:|---|---|
| audit100_002 | assignment_rubric:000060:9448a3aea71c | assignment_rubric | long | minor_repair | minor | 4 | critical_omission, requirement_or_constraint_loss | The existing target is faithful, clear, and mostly captures the assignment brief and rubric at a high level. However, it omits some important rubric constraints, especially the need for formal objective style, coherent flow, concrete technical mechanisms, hedged claims, specific evaluation metrics, and a few strict formatting/content requirements around numerical metrics and electrolyte description. These omissions do not make the label wrong, but a stronger summary would preserve more of the rubric’s scoring emphasis. |
| audit100_004 | tech_doc:000015:66971f2227af | tech_doc | long | minor_repair | minor | 4 | unsupported_fact | The target captures the tutorial’s main purpose and most major steps clearly. However, the final key point slightly overstates the provided source by saying the controller is connected to the other interface items; the excerpt only shows connecting the controller to the first text field, though it says the parts need to be connected. A small wording change would make it fully faithful. |
| audit100_035 | academic_paper:000169:5206c483c2af | academic_paper | medium | minor_repair | minor | 4 | critical_omission, too_detailed | The target is mostly faithful and captures the main themes: Cu nanoparticle preparation, glycerol's stabilizing/protective role, and optimization of nitrobenzene reduction to aniline. However, some key points are more detailed than ideal for high-level reading support, especially the reagent-by-reagent synthesis description and exact particle-size details. It also omits the later discussion of ultrasound treatment to address nanoparticle aggregation and measure dispersion, which is a meaningful part of the excerpt. |
| audit100_055 | academic_paper:000414:f2dfdd19f418 | academic_paper | medium | minor_repair | minor | 4 | source_instruction_following_risk | The target is mostly faithful, clear, and appropriately high-level. It captures the test package, measurement setup, FEA simulation, and PCB-based calibration. The only notable issue is that one key point says the FEA tool simulated stress from assembly, operation, and bending tests, while the source presents some of these as tool capabilities and says the present study used the tool for warpage from thermo-mechanical stress. A small wording repair would avoid implying all listed capabilities were performed in this study. |
| audit100_072 | medlineplus:000013:89d4b8445916 | medlineplus | medium | minor_repair | minor | 4 | critical_omission, medical_or_safety_nuance_loss | The target is faithful, clear, well structured, and mostly captures the main shingles overview. However, the source has a substantial section on possible complications, including long-term nerve pain and vision, hearing, balance, or rare life-threatening problems. The existing target only briefly mentions complications in relation to the vaccine, so it loses an important medical warning. A small repair can preserve that nuance while keeping the summary high-level. |
| audit100_079 | medlineplus:000105:8cf02bc7841d | medlineplus | medium | minor_repair | minor | 4 | medical_or_safety_nuance_loss | The target is faithful, clear, well structured, and captures the main ideas about what colds are, how they spread, symptoms, treatment, antibiotics, and prevention. However, it omits the source's important medical warning that some people can develop complications and should contact a provider for concerning symptoms such as breathing trouble, dehydration, persistent fever, symptoms lasting or worsening, or worsening chronic conditions. This is a minor medical safety nuance loss rather than a major failure because the summary is otherwise accurate and useful. |
| audit100_093 | gen_know:000028:f27b17bee9eb | gen_know | medium | minor_repair | minor | 4 | critical_omission | The target is mostly faithful, clear, and well structured, and it captures Carleton's military career and role in New Brunswick. However, it omits the prominent caveat from the source that he was absent in England for the last fourteen years of his tenure and refused orders to return, which makes the statement that he 'remained in the post until his death' somewhat incomplete and potentially misleading. |
| audit100_016 | academic_book:000107:07d160f2a15b | academic_book | medium | minor_repair | minor | 5 | requirement_or_constraint_loss | The target is mostly faithful, clear, and high-level, and it captures the shift from total revenue/total cost analysis to marginal revenue/marginal cost analysis. The main weakness is a slight ambiguity in the first two key points: the source distinguishes profit maximization from the case where losses are unavoidable, while the target can sound as if the firm both earns $90 profit and suffers losses in the same situation. A small wording repair would make the loss-minimization condition clearer. |
| audit100_071 | public_service:000193:a7d94bf1143f | public_service | medium | minor_repair | minor | 5 | requirement_or_constraint_loss | The target is clear, high-level, and mostly faithful. It captures the eligibility requirements, education substitution, exemptions, and license classes. A minor repair would improve precision by noting that supervisor or foreman experience can also qualify and by phrasing the $1,000 exemption as the source states it rather than as general low-value work. |
| audit100_094 | gen_know:000066:644d17a70219 | gen_know | long | minor_repair | minor | 5 | unsupported_fact | The target is mostly faithful, clear, and appropriately high-level. It captures Madsen's biography, party and trade-union roles, parliamentary service, cabinet posts, and wartime imprisonment. The only notable issue is the phrase 'later retirement,' which is not directly stated; the source says he left politics after World War II, not necessarily that he retired generally. |
| audit100_001 | assignment_rubric:000022:1ef17fdf008b | assignment_rubric | long | accept | none | 5 | none | The target correctly treats the source as an assignment brief and rubric rather than trying to complete the assignment. It faithfully captures the main requirements: summarize one specific research paper, cover objectives, methods, technical details, results, clinical relevance, interpretability, ethics, limitations, style, organization, and length. The four key points are distinct, high-level, and useful for reading-support summarization. |
| audit100_003 | tech_doc:000009:ed7079f208ff | tech_doc | medium | accept | none | 5 | none | The target is faithful and concise, focusing on the tutorial's main explanation of Python while loops, repeated indented code, stopping conditions, syntax, examples, and infinite-loop warning. It omits some minor details such as equality operators, single-line output, and the exercise, but these are not central enough to require inclusion in a high-level reading-support summary. |


## Interpretation

The audit results suggest that the current training labels are not the main reason smaller models have underperformed the earlier 8B baseline. The sampled labels were usually faithful, concise, high-level, and structurally aligned with the required JSON output format. The few weaknesses were minor rather than systemic.

The most common minor issues were:

- missing some rubric or requirement details in long assignment-style sources;
- losing some medical or safety nuance in health-related pages;
- including slightly too much technical detail in some academic-paper summaries;
- using a phrase that was reasonable but not directly supported by the source.

These issues are worth tracking, but they do not justify rebuilding the whole dataset. A full relabeling pass would add cost and risk without strong evidence that it would materially improve the next training stage.

## Implications For The Small-Model Search

This audit supports continuing the small-model search using the current frozen dataset. Since the labels appear broadly reliable, the next work should focus on model-side factors:

- comparing the shortlisted 3B-scale candidates under the same training and validation process;
- refining learning rate, epoch count, LoRA rank, LoRA alpha, and dropout around the strongest checkpoints;
- selecting checkpoints by validation quality before running the final frozen benchmark;
- using targeted prompt/schema guards only as inference controls, not as a substitute for training quality.

The audit also suggests that future data work should be targeted rather than broad. If later validation errors cluster around medical nuance, long rubrics, or technical academic passages, those specific groups can be audited or repaired without replacing the entire dataset.

## Recommendation

The current frozen training dataset should remain the baseline for the next round of fine-tuning experiments. No broad target-output rewrite is recommended at this stage.

A small optional repair file may be kept for the 10 sampled minor-repair cases, but those repairs should not overwrite the original dataset. Any future repaired dataset should be versioned separately, with the original source, original target, revised target, reviewer model, and repair reason recorded.

## Limitations

This audit is based on a 100-pair random sample from the training split, not a full review of all 1162 training examples. The sample includes all major source domains and length buckets, but rare dataset problems may still exist outside the sample. The review also evaluates target-label quality rather than downstream model behavior, so it should be combined with validation-set inference and benchmark scoring when selecting the final model.

## Artifacts

- Sample with source and target text: `<external-local-raw-3b-search-workspace-not-in-git>/outputs/data_audit/random_sample_100_20260513/sample_with_text.jsonl`
- Public sample manifest without raw text: `<external-local-raw-3b-search-workspace-not-in-git>/outputs/data_audit/random_sample_100_20260513/sample_manifest_public.json`
- API audit outputs: `<external-local-raw-3b-search-workspace-not-in-git>/outputs/data_audit/random_sample_100_20260513/api_audit_outputs.jsonl`
- API raw requests: `<external-local-raw-3b-search-workspace-not-in-git>/outputs/data_audit/random_sample_100_20260513/raw_api_requests.jsonl`
- API raw responses: `<external-local-raw-3b-search-workspace-not-in-git>/outputs/data_audit/random_sample_100_20260513/raw_api_responses.jsonl`
- Machine-readable summary: `<external-local-raw-3b-search-workspace-not-in-git>/outputs/data_audit/random_sample_100_20260513/audit_summary.json`
- Minor repair candidate exports: `<external-local-raw-3b-search-workspace-not-in-git>/outputs/data_audit/random_sample_100_20260513/minor_repair_candidates.jsonl`
