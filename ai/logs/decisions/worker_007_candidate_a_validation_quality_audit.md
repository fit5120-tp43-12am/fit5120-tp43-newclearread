# Worker 007 Candidate A Validation Quality Audit

Date/time: 2026-04-28T17:53:55+10:00

## Scope

- Executed `work_orders/007_candidate_a_validation_quality_audit.md`.
- Evaluated Candidate A on validation split only.
- Did not use `data/splits/test.jsonl`.
- Did not run training.
- Did not modify source splits, teammate exports, source datasets, or the Candidate A adapter.

## Commands Run

```bash
python -m py_compile scripts/evaluate_candidate_a_validation.py scripts/run_inference_check.py
python scripts/evaluate_candidate_a_validation.py --config configs/train_llama31_8b_qlora_candidate_a.yaml --adapter-path models/adapters/full_candidate_a_3epoch --data-path data/splits/val.jsonl --output-dir outputs/evaluation/candidate_a_validation
python scripts/evaluate_candidate_a_validation.py --config configs/train_llama31_8b_qlora_candidate_a.yaml --adapter-path models/adapters/full_candidate_a_3epoch --data-path data/splits/val.jsonl --output-dir outputs/evaluation/candidate_a_validation --reuse-predictions
```

The first full evaluation exposed that the mojibake pattern literals in the new script needed Unicode escapes. After fixing that and refining false-positive meta phrase matching, the full validation generation was rerun with the corrected script. The reuse command then refreshed deterministic flags without reloading the model.

## Local Outputs

- `scripts/evaluate_candidate_a_validation.py`
- `reports/CANDIDATE_A_VALIDATION_QUALITY_REPORT.md`
- `logs/candidate_a_validation_quality_audit.md`
- `logs/decisions/worker_007_candidate_a_validation_quality_audit.md`
- `outputs/evaluation/candidate_a_validation/validation_predictions.jsonl`
- `outputs/evaluation/candidate_a_validation/validation_metrics.json`
- `TRAINING_MEMORY.md` provisional update

The prediction JSONL and metrics JSON are local artifacts only and must not be committed unless the central brain later approves.

## Prediction Run

- Validation records generated: `145/145`
- Validation SHA256: `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- Final corrected generation timing: `2026-04-28T17:40:57+10:00` to `2026-04-28T17:52:35+10:00`
- Elapsed: `11m 38s`
- Average seconds/example: `4.814`
- Progress printed for every validation example with elapsed time, average seconds/example, estimated remaining time, and ETA.

## Deterministic Metrics

- JSON parse rate: `145/145` (`100.00%`)
- Schema pass rate: `145/145` (`100.00%`)
- Exact key order rate: `145/145` (`100.00%`)
- `main_idea` string rate: `145/145` (`100.00%`)
- `key_points` list rate: `145/145` (`100.00%`)
- Exactly 4 key points rate: `145/145` (`100.00%`)
- All key points strings rate: `145/145` (`100.00%`)
- Approximate `main_idea` two-sentence compliance: `144/145` (`99.31%`)
- Approximate each-key-point one-sentence compliance: `143/145` (`98.62%`)
- Empty-string rows: `0`
- Output too short / too long: `0 / 0`
- Average `main_idea` words: `32.4`
- Average key-point words: `16.67`
- Code fence / markdown leakage: `0`
- Extra text outside JSON: `0`
- Refusal/meta-response phrases: `0`

Domain and natural-length-bucket breakdowns are in `reports/CANDIDATE_A_VALIDATION_QUALITY_REPORT.md` and `outputs/evaluation/candidate_a_validation/validation_metrics.json`.

## Encoding And Mojibake Audit

- Prediction mojibake rows: `0`
- Gold assistant mojibake rows: `0`
- Scanned required work-order patterns and additional variants using Unicode-escaped literals in the script.
- No prediction or gold target contained the scanned mojibake artifacts.

## Manual Review

- Reviewed 16 validation examples.
- Coverage: at least 2 examples from each domain; short, medium, and long buckets included.
- Labels: `pass` 14, `minor_issue` 2, `major_issue` 0, `uncertain` 0.
- Assignment/rubric examples were summarized as prompts/rubrics; Candidate A did not follow embedded instructions.
- Medical and public-service warnings/restrictions were generally preserved.
- Minor issues:
  - one public-service example copied a noisy fee detail into an awkward unsupported amount;
  - one general-knowledge example slightly muddled attribution around a historical/name detail.

## Recommendation

Recommendation: `proceed_to_final_evaluation`.

Candidate A should be sent to central-brain review and final test evaluation planning. Candidate B is not recommended from this validation audit because format/schema quality is excellent, sentence compliance is strong, no domain or length bucket fails broadly, mojibake is absent, and manual review found no major faithfulness or instruction-following issue.

Final evaluation should still watch public-service exact numeric details, especially fees and time windows.

## Git Result

Pending at time of initial log. This section should be updated after mirroring Git-safe files, committing, pushing, and running Git safety checks.
