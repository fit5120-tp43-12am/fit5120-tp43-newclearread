# Candidate A Validation Quality Audit Log

Date/time: 2026-04-28T17:53:55+10:00

## Scope

- Validation split only.
- No test-set use.
- No training.

## Inputs

- Config: `ai/lora_training/configs/train_llama31_8b_qlora_candidate_a.example.yaml`
- Adapter: `ai/lora_training/models/adapters/full_candidate_a_3epoch`
- Data: `ai/lora_training/data/splits/val.jsonl`
- Split manifest: `ai/lora_training/data/splits/split_manifest.json`

## Outputs

- Predictions JSONL: `ai/lora_training/outputs/evaluation/candidate_a_validation/validation_predictions.jsonl`
- Metrics JSON: `ai/lora_training/outputs/evaluation/candidate_a_validation/validation_metrics.json`
- Report: `reports/CANDIDATE_A_VALIDATION_QUALITY_REPORT.md`

## Result Summary

- Validation records: `145` expected `145`
- Validation SHA256: `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- Generation elapsed: `11m 38s`
- Average seconds/example: `4.814`
- JSON parse: `145/145`
- Schema pass: `145/145`
- Main idea two sentences: `144/145`
- Each key point one sentence: `143/145`
- Prediction mojibake rows: `0`
- Gold mojibake rows: `0`

## Manual Review Summary

- Reviewed 16 validation examples.
- Coverage: at least 2 examples from each domain; short, medium, and long buckets included.
- Labels: `pass` 14, `minor_issue` 2, `major_issue` 0, `uncertain` 0.
- Assignment/rubric examples were summarized as source text; Candidate A did not follow embedded instructions.
- Medical/public-service warnings and restrictions were generally preserved.
- One public-service example copied a noisy fee detail into an awkward unsupported amount; this is isolated and should be watched during final evaluation.

## Recommendation

Recommendation: `proceed_to_final_evaluation`.

Rationale: deterministic format/schema quality is very high, domain and length breakdowns do not show broad failure, mojibake was absent in predictions and gold assistant targets under the scanned patterns, and manual review found no major faithfulness or instruction-following issue.
