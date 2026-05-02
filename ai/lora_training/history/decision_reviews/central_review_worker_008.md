# Central-Brain Review: Worker 008 Final Test Evaluation Candidate A

Date/time: 2026-04-28

## Decision

Result: pass with final-selection note.

Candidate A is selected as the final raw LoRA adapter for the current training cycle.

This selection is made with an explicit deployment caveat: raw generation produced one held-out schema miss, so production/local inference must use a schema guard. The guard must validate the exact JSON contract and must not expose invalid outputs directly to users.

No Candidate B should be trained from this test result. The test set has now been used, so using the single schema miss to tune and re-evaluate would contaminate the held-out evaluation.

## Evidence Reviewed

Local files reviewed:

```text
ai/lora_training/scripts/evaluate_final_test_candidate_a.py
ai/lora_training/reports/FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md
ai/lora_training/history/run_logs/final_test_evaluation_candidate_a.md
ai/lora_training/history/decision_reviews/worker_008_final_evaluation_candidate_a.md
ai/lora_training/outputs/evaluation\candidate_a_test\test_predictions.jsonl
ai/lora_training/outputs/evaluation\candidate_a_test\test_metrics.json
```

Key Worker 008 results:

- test records evaluated: `145/145`
- test SHA256: `6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f`
- split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- generation runtime: `11m 50s`
- average generation speed: `4.899` seconds/example
- JSON parse: `145/145`
- schema pass: `144/145`
- exact key order: `145/145`
- exactly 4 key points: `144/145`
- all key points strings: `145/145`
- main idea two-sentence heuristic: `144/145`
- each-key-point one-sentence heuristic: `144/145`
- empty/too-short/too-long/markdown leakage/extra text/refusal/meta/mojibake: `0`
- manual review: `pass` 14, `minor_issue` 2, `major_issue` 1, `uncertain` 0

## Independent Verification

Central-brain reran compile and metrics JSON checks in WSL env `clearread-llama-lora`:

```bash
python -m py_compile scripts/evaluate_final_test_candidate_a.py
python -m json.tool outputs/evaluation/candidate_a_test/test_metrics.json
```

Result: pass.

Central-brain independently parsed `test_metrics.json` and confirmed:

```text
test_count: 145
expected_test_count: 145
test_count_matches_expected: true
json_parse_ok: 145
schema_pass: 144
exactly_4_key_points: 144
main_idea_two_sentences: 144
each_key_point_one_sentence: 144
prediction_mojibake_count: 0
gold_mojibake_count: 0
test_sha256: 6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f
split_manifest_sha256: 42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19
```

Central-brain independently parsed `test_predictions.jsonl` and confirmed:

```text
rows: 145
schema_status == pass: 144
deterministic_flags.json_parse_ok: 145
deterministic_flags.schema_pass: 144
deterministic_flags.exactly_4_key_points: 144
```

The only schema failure is:

```text
row: 87
record_id: academic_paper:000458:8541ac16b79f
domain: academic_paper
natural_length_bucket: medium
schema_errors: key_points_len_7
```

Central-brain inspected row 87's generated output. It is parseable JSON and broadly faithful, but it has seven key points instead of the required four. This is a real output-contract failure, not a parser artifact.

Central-brain verified test split hashes:

```text
test.jsonl: 6613390F654C55A69C5DDB90234F81005FC3BACA8E57651206F1EF024C939B7F
split_manifest.json: 42BFE9974C31E74B98B45D45DAA792F8582D517541E153439B510E9A9B307F19
```

Central-brain searched Worker 008 script/report/logs for training calls and inappropriate split usage. The script requires `--allow-heldout-test`, only allows `test.jsonl`, and the only train/validation/Candidate B mentions are scope statements. No training call was found.

## Git Verification

Team repo:

```text
<team-repo-root>
```

Central-brain verified:

- branch: `feature/ai-llama-lora-training`
- local HEAD: `761db92d91b704b4222633b526dd71cc0c9b9ce6`
- upstream HEAD: `761db92d91b704b4222633b526dd71cc0c9b9ce6`
- latest commits:
  - `761db92 docs(ai): record worker 008 final evaluation result`
  - `f53e1fe feat(ai): add final candidate a test evaluation`

Git safety checks returned no tracked raw data or model binary artifacts:

```text
git ls-files 'ai/**/*.jsonl' -> empty
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin' -> empty
```

Central-brain also checked the repo-side `ai` tree and found no test prediction JSONL, metrics JSON, outputs folder, or model binary artifacts.

## Final Selection

Selected model artifact for this training cycle:

```text
ai/lora_training/models/adapters/full_candidate_a_3epoch
```

Base model:

```text
unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
```

Training route:

```text
Llama-3.1-8B-Instruct + SFT + QLoRA
```

Important caveat:

- Raw model held-out schema compliance is `144/145` (`99.31%`).
- The final deployment/run wrapper must enforce exact output shape:

```json
{"main_idea":"...","key_points":["...","...","...","..."]}
```

- Invalid raw outputs must be repaired safely, retried, or rejected rather than returned directly.

## Next Decision

Proceed to artifact packaging and local deployment notes.

Worker 009 should organize final artifact metadata, write a local inference/runbook, and implement or document a schema guard around Candidate A. It must not train, tune, rerun final test evaluation for model selection, or commit adapter/model artifacts to normal Git.
