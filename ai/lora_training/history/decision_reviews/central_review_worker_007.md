# Central-Brain Review: Worker 007 Candidate A Validation Quality Audit

Date/time: 2026-04-28

## Decision

Result: pass.

Worker 007 completed a validation-only quality audit for Candidate A. The evidence supports proceeding to final test evaluation with Candidate A. Candidate B is not recommended at this point.

Candidate A is now selected for final test evaluation, but it is not yet declared the final model artifact until the held-out test evaluation is reviewed.

## Evidence Reviewed

Local files reviewed:

```text
ai/lora_training/scripts/evaluate_candidate_a_validation.py
ai/lora_training/reports/CANDIDATE_A_VALIDATION_QUALITY_REPORT.md
ai/lora_training/history/run_logs/candidate_a_validation_quality_audit.md
ai/lora_training/history/decision_reviews/worker_007_candidate_a_validation_quality_audit.md
ai/lora_training/outputs/evaluation\candidate_a_validation\validation_predictions.jsonl
ai/lora_training/outputs/evaluation\candidate_a_validation\validation_metrics.json
```

Key reported result:

- validation records evaluated: `145/145`
- validation SHA256: `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be`
- split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- generation runtime: `11m 38s`
- average generation speed: `4.814` seconds/example
- JSON parse/schema/key-order compliance: `145/145`
- exactly 4 key points and all string fields: `145/145`
- main idea two-sentence heuristic: `144/145`
- key-point one-sentence heuristic: `143/145`
- empty/too short/too long/markdown leakage/extra text/refusal/meta: `0`
- prediction mojibake rows: `0`
- gold assistant mojibake rows: `0`
- manual review: `pass` 14, `minor_issue` 2, `major_issue` 0, `uncertain` 0
- recommendation: `proceed_to_final_evaluation`

## Independent Verification

Central-brain reran compile checks in WSL env `clearread-llama-lora`:

```bash
python -m py_compile scripts/evaluate_candidate_a_validation.py scripts/run_inference_check.py
```

Result: pass.

Central-brain verified `validation_metrics.json` is valid JSON using WSL Python:

```bash
python -m json.tool outputs/evaluation/candidate_a_validation/validation_metrics.json
```

Result: pass.

Central-brain independently parsed local metrics and confirmed:

```text
validation_count: 145
expected_validation_count: 145
validation_count_matches_expected: true
schema_pass: 145
json_parse_ok: 145
main_idea_two_sentences: 144
each_key_point_one_sentence: 143
prediction_mojibake_count: 0
gold_mojibake_count: 0
validation_sha256: a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be
split_manifest_sha256: 42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19
```

Central-brain independently parsed `validation_predictions.jsonl` and confirmed:

```text
rows: 145
schema_status == pass: 145
deterministic_flags.json_parse_ok: 145
deterministic_flags.schema_pass: 145
prediction mojibake rows from deterministic_counts: 0
gold mojibake rows from deterministic_counts: 0
```

Central-brain checked the previously suspicious validation rows with Python UTF-8 parsing. The `Bash` sample contains proper Unicode `Bashō’s` with no non-ASCII mojibake code points in the inspected preview. The earlier mojibake-looking display was a terminal/rendering artifact, not dataset corruption.

Central-brain searched Worker 007 script/report/log for test-set usage and training calls. The only `test.jsonl` hits are explicit refusal/scope statements:

```text
if data_path.name == "test.jsonl": raise ValueError(...)
Did not use data/splits/test.jsonl
```

No training call was found.

## Git Verification

Team repo:

```text
<team-repo-root>
```

Central-brain verified:

- branch: `feature/ai-llama-lora-training`
- local HEAD: `8e5aeae6db2dcb79b7dd9fbfb0a7b31408916a8a`
- upstream HEAD: `8e5aeae6db2dcb79b7dd9fbfb0a7b31408916a8a`
- latest commits:
  - `8e5aeae docs(ai): finalize worker 007 git record`
  - `40ebc74 docs(ai): record worker 007 validation audit result`
  - `2adc1f2 feat(ai): add candidate a validation audit`

Git safety checks returned no tracked raw data or model binary artifacts:

```text
git ls-files 'ai/**/*.jsonl' -> empty
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin' -> empty
```

Central-brain also checked the repo-side `ai` tree and found no `outputs`, `validation_predictions`, `validation_metrics`, JSONL files, or model binary artifacts.

## Notes

- Windows PowerShell `ConvertFrom-Json` may fail if it reads `validation_metrics.json` with the wrong default encoding because the file contains non-ASCII mojibake-pattern strings. WSL/Python UTF-8 parsing succeeds, so the metrics file itself is valid.
- The manual review found two minor issues:
  - one public-service example copied a noisy fee detail into an awkward unsupported amount;
  - one general-knowledge example slightly muddled a historical/name attribution.
- These are not broad failures. Final test evaluation should specifically watch public-service numeric details, fees, time windows, and named-entity attribution.

## Next Decision

Proceed to final held-out test evaluation with Candidate A.

Candidate B is skipped for now. Do not train or tune further unless final evaluation reveals a blocking issue and the central brain explicitly reopens the model-selection phase.
