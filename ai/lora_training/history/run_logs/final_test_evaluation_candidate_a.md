# Final Test Evaluation Candidate A Log

Date/time: 2026-04-28T18:29:42+10:00

## Scope

- Final held-out test split only.
- No training, tuning, or Candidate B.

## Inputs

- Config: `ai/lora_training/configs/train_llama31_8b_qlora_candidate_a.example.yaml`
- Adapter: `ai/lora_training/models/adapters/full_candidate_a_3epoch`
- Data: `ai/lora_training/data/splits/test.jsonl`
- Split manifest: `ai/lora_training/data/splits/split_manifest.json`

## Outputs

- Predictions JSONL: `ai/lora_training/outputs/evaluation/candidate_a_test/test_predictions.jsonl`
- Metrics JSON: `ai/lora_training/outputs/evaluation/candidate_a_test/test_metrics.json`
- Report: `reports/FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md`

## Result Summary

- Test records: `145` expected `145`
- Test SHA256: `6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- Generation elapsed: `11m 50s`
- Average seconds/example: `4.899`
- JSON parse: `145/145`
- Schema pass: `144/145`
- Main idea two sentences: `144/145`
- Each key point one sentence: `144/145`
- Prediction mojibake rows: `0`
- Gold mojibake rows: `0`

## Deterministic Failure Notes

- Row 66 (`academic_paper`, `short`) failed only the approximate main-idea sentence-count heuristic because the output contains `E. coli`; manual review judged the output valid and faithful.
- Row 87 (`academic_paper`, `medium`) failed schema because the output contained 7 key points instead of exactly 4.

## Manual Review Summary

- Reviewed 17 final test examples.
- Coverage: at least 2 examples from each domain; short, medium, and long buckets included.
- Required focus areas included `medlineplus`, `public_service`, `assignment_rubric`, long academic examples, deterministic failures, and public-service examples with fees, numbers, eligibility rules, and time windows.
- Labels: `pass` 14, `minor_issue` 2, `major_issue` 1, `uncertain` 0.
- Major issue: one schema-contract failure on row 87 with 7 key points.
- Minor issues: one public-service summary omitted the one-or-two-week visa processing window; one general-knowledge summary appears to fuse a 1998 party-role detail with a 1999 Smer timing detail.

## Recommendation

Recommendation: `select_with_schema_guard`.

Rationale: Candidate A is strong overall and does not show broad domain, length, safety, instruction-following, or encoding collapse. The single held-out schema failure is isolated but important enough that model-selection review should decide whether to accept Candidate A as the final artifact.
