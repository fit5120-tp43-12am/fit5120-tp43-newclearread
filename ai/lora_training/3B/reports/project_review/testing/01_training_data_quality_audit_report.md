# Training Data Quality Audit Report

## Project Purpose

The project aimed to reduce the deployment cost of the ClearRead summarisation system by moving from the earlier Llama 3.1 8B Candidate A model to a smaller 3B-4B model. The target task was stable and narrow: produce a short reading-support summary for an article chunk of about 600 words.

The expected output shape was:

```json
{"main_idea":"two short faithful sentences","key_points":["...","...","...","..."]}
```

The data audit checked whether the training labels were strong enough for small-model fine-tuning before more model-side experiments were continued.

## Work Completed

A fixed random sample of 100 training pairs was selected from the frozen training split. The full training split contained 1162 examples. The audit reviewed source text and target output quality across all major source domains and length buckets.

| Item | Value |
|---|---|
| Training split size | 1162 pairs |
| Sample size | 100 pairs |
| Sampling method | Fixed-seed random sample |
| Random seed | 20260513 |
| Review schema | `training_pair_quality_audit_v1` |
| Reviewer model | `gpt-5.5` |

Each pair was reviewed for faithfulness, coverage, high-level abstraction, clarity, schema fit, and training value.

## Rationale

Early 3B experiments showed that smaller models were sensitive to epoch count, LoRA rank, learning rate, and prompt guards. The audit checked whether the quality gap came from weak target labels or from model capacity and training settings. This step protected the later search from spending time on parameter tuning when the underlying labels might have needed repair.

## Verification Results

The sample covered seven source domains:

| Source domain | Count |
|---|---:|
| academic_paper | 35 |
| medlineplus | 16 |
| academic_book | 14 |
| gen_know | 13 |
| public_service | 12 |
| tech_doc | 8 |
| assignment_rubric | 2 |

Length coverage:

| Length bucket | Count |
|---|---:|
| short | 13 |
| medium | 75 |
| long | 12 |

Audit decisions:

| Decision | Count |
|---|---:|
| Accept as-is | 90 |
| Minor repair | 10 |
| Rewrite | 0 |
| Drop or manual review | 0 |

Mean scores:

| Dimension | Mean out of 5 |
|---|---:|
| Faithfulness | 4.94 |
| Coverage | 4.89 |
| High-level abstraction | 4.86 |
| Clarity and accessibility | 4.97 |
| Schema/style fit | 5.00 |
| Training value | 4.93 |

The audit found strong training-label quality overall. The main minor issues involved long assignment rubrics, medical warning nuance, technical detail selection, and occasional source precision.

## Deployment Observations And Handling

The audit supported continued use of the current frozen training data for model search. Minor issue tags were recorded for health warnings, rubric constraints, unsupported wording, and overly detailed academic-paper summaries. These tags provide a useful guide for future targeted repairs.

The current product can accept a dynamic number of key points. The audit still kept schema checks visible because stable JSON remains important for integration and downstream handling.

## Final Conclusion

The training data was suitable for the 3B-scale search. The evidence supported continued model-side work with the existing frozen dataset. A broad relabeling pass was unnecessary for this stage.

## Evidence Locations

| Evidence | Path |
|---|---|
| Source report | `reports/data_audit/training_pair_random_audit_100_20260513.md` |
| Final package manifest | `manifests/package_manifest.json` |
| Evidence inventory | `reports/evidence/evidence_inventory.md` |
| Evidence allocation matrix | `reports/project_review/index/EVIDENCE_TO_REPORT_MATRIX.md` |
