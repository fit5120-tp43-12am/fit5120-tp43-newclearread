# Worker 008 Final Evaluation Candidate A

Date/time: 2026-04-28

## Scope

- Executed `work_orders/008_final_evaluation_candidate_a.md`.
- Used the approved held-out test split: `data/splits/test.jsonl`.
- Evaluated only Candidate A adapter: `models/adapters/full_candidate_a_3epoch`.
- Did not run training, tune hyperparameters, change decoding settings for model selection, or run Candidate B.

## Commands Run

```bash
python -m py_compile scripts/evaluate_final_test_candidate_a.py
python scripts/evaluate_final_test_candidate_a.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --adapter-path models/adapters/full_candidate_a_3epoch --data-path data/splits/test.jsonl --output-dir outputs/evaluation/candidate_a_test --allow-heldout-test
```

Both commands were run from WSL inside the `clearread-llama-lora` conda environment.

## Local Outputs

- `scripts/evaluate_final_test_candidate_a.py`
- `reports/FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md`
- `logs/final_test_evaluation_candidate_a.md`
- `logs/decisions/worker_008_final_evaluation_candidate_a.md`
- `outputs/evaluation/candidate_a_test/test_predictions.jsonl`
- `outputs/evaluation/candidate_a_test/test_metrics.json`

The prediction JSONL and metrics JSON are local artifacts and should not be committed unless central brain later explicitly approves.

## Deterministic Results

- Test records evaluated: `145/145`
- Test SHA256: `6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- Generation runtime: `11m 50s`
- Average generation speed: `4.899` seconds/example
- JSON parse: `145/145`
- Schema pass: `144/145`
- Exact key order: `145/145`
- `main_idea` string: `145/145`
- `key_points` list: `145/145`
- Exactly 4 key points: `144/145`
- All key points strings: `145/145`
- Approximate `main_idea` two-sentence compliance: `144/145`
- Approximate each-key-point one-sentence compliance: `144/145`
- Empty strings, too-short/too-long outputs, markdown/code-fence leakage, extra text outside JSON, refusal/meta responses, prediction mojibake rows, and gold mojibake rows: `0`
- Average `main_idea` word count: `33.02`
- Average key-point word count: `16.8`

## Failure Notes

- Row 66 (`academic_paper`, `short`) failed only the approximate main-idea sentence-count heuristic because the output contains `E. coli`; manual review judged the output valid and faithful.
- Row 87 (`academic_paper`, `medium`) failed schema because the output contained 7 key points instead of exactly 4.

## Manual Review

- Reviewed 17 final test examples.
- Coverage included at least 2 examples from each of the 7 domains, short/medium/long buckets, `medlineplus`, `public_service`, `assignment_rubric`, long academic examples, both deterministic failures, and public-service examples with fees, numbers, eligibility rules, and time windows.
- Manual labels: `pass` 14, `minor_issue` 2, `major_issue` 1, `uncertain` 0.
- No refusal/meta behavior, instruction-following failure, medical/public-service safety warning reversal, or broad domain/length collapse was found.

## Recommendation

Recommendation: `central_review_required_before_final_selection`.

Candidate A is strong overall, but one held-out test row violated the exact 4-key-point contract. This is not a `do_not_select_without_fix` result, but central brain should decide whether the isolated schema miss is acceptable before declaring Candidate A the selected final artifact.

## Git Result

Git-safe files were mirrored to the team repo under:

- `ai/scripts/evaluate_final_test_candidate_a.py`
- `ai/reports/FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md`
- `ai/logs/final_test_evaluation_candidate_a.md`
- `ai/logs/decisions/worker_008_final_evaluation_candidate_a.md`

Primary pushed commit:

```text
f53e1fe3b8ad9097e0aaedcc24a2182265cfe123 feat(ai): add final candidate a test evaluation
```

Branch pushed:

```text
origin/feature/ai-llama-lora-training
```

Safety checks after the primary push:

```text
git ls-files 'ai/**/*.jsonl' -> empty
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin' -> empty
```

Local HEAD and upstream HEAD both resolved to `f53e1fe3b8ad9097e0aaedcc24a2182265cfe123` after the primary push.

This updated worker decision log is intended to be pushed in a follow-up docs/log commit so the repo records the primary commit result.
