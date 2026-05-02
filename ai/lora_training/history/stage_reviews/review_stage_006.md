# Project Review: Stage 006 Full Training Candidate A

Date/time: 2026-04-28

## Decision

Result: pass with notes.

Stage 006 successfully completed Candidate A full training:

```text
Llama-3.1-8B-Instruct + SFT + QLoRA, 3 epochs
```

Candidate A is viable for validation-quality review. It is not yet declared the final model because the current evidence is mostly training loss, validation loss, and schema checks on 10 validation examples.

## Evidence Reviewed

Local files reviewed:

```text
ai/lora_training/configs/train_llama31_8b_qlora_candidate_a.example.yaml
ai/lora_training/scripts/train_full_qlora.py
ai/lora_training/scripts/run_inference_check.py
ai/lora_training/history/run_logs/full_train_candidate_a_3epoch.md
ai/lora_training/reports/FULL_TRAIN_CANDIDATE_A_REPORT.md
ai/lora_training/history/stage_reviews/stage_006_train_candidate_a_3epoch.md
```

Key Stage 006 results:

- train/validation counts: `1162/145`
- train SHA256: `B99CAA6B06963A05CA7E32DA3C3BE3237C9EA6B128CE1CCF329B78D2D56929FB`
- validation SHA256: `A7CF5277EDA97EF1868376CAA79343B040BA6920602BC607DC145A2039D2D4BE`
- split manifest SHA256: `42BFE9974C31E74B98B45D45DAA792F8582D517541E153439B510E9A9B307F19`
- preflight truncation: train `0`, validation `0`
- trainable assistant labels: non-empty for all train/validation records
- trainable labels parsed as JSON for all train/validation records
- training steps: `438`
- final train loss: `0.4797596574748216`
- validation loss: `0.9654271602630615`
- validation schema check: `10/10`
- training runtime: `1h 04m 39s`
- final ETA callback average: `8.68` seconds per optimizer step
- test set: not used

## Independent Verification

Independent review verified local split hashes:

```text
train.jsonl: B99CAA6B06963A05CA7E32DA3C3BE3237C9EA6B128CE1CCF329B78D2D56929FB
val.jsonl: A7CF5277EDA97EF1868376CAA79343B040BA6920602BC607DC145A2039D2D4BE
split_manifest.json: 42BFE9974C31E74B98B45D45DAA792F8582D517541E153439B510E9A9B307F19
```

Independent review verified local line counts:

```text
train: 1162
validation: 145
```

Independent review verified the Candidate A adapter directory exists:

```text
ai/lora_training/models/adapters/full_candidate_a_3epoch
```

Adapter directory contents:

| File | Size bytes |
|---|---:|
| `adapter_config.json` | 1262 |
| `adapter_model.safetensors` | 167832240 |
| `chat_template.jinja` | 4614 |
| `README.md` | 5256 |
| `tokenizer.json` | 17209920 |
| `tokenizer_config.json` | 50669 |

Independent review reran compile verification in WSL env `clearread-llama-lora`:

```bash
python -m py_compile scripts/training_data_utils.py scripts/verify_assistant_loss_mask.py scripts/train_full_qlora.py scripts/run_inference_check.py
```

Result: pass.

Independent review independently reran validation inference against Candidate A:

```bash
python scripts/run_inference_check.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --adapter-path models/adapters/full_candidate_a_3epoch --data-path data/splits/val.jsonl --num-examples 5
```

Result:

```text
status: ok
checked: 5
schema_pass: 5
```

Independent review searched Candidate A config/script/log/report for test-set usage. The only hit was the report instruction saying not to use the test set until project review selection. No `test.jsonl` path was used.

## Git Verification

Team repo:

```text
<team-repo-root>
```

Independent review verified:

- branch: `feature/ai-llama-lora-training`
- local HEAD: `f97b06387209975ee639beb6bf3c862abdb7db7a`
- upstream HEAD: `f97b06387209975ee639beb6bf3c862abdb7db7a`
- latest commits:
  - `f97b063 docs(ai): finalize stage 006 git record`
  - `7a637a8 docs(ai): record stage 006 training result`
  - `cdba362 feat(ai): train candidate a qlora workflow`

artifact storage checks returned no tracked raw data or model binary artifacts:

```text
git ls-files 'ai/**/*.jsonl' -> empty
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin' -> empty
```

## Notes

- Candidate A looks technically healthy: no OOM, no truncation, all validation schema checks passed in the sampled runs, and the adapter saved correctly.
- The validation loss `0.9654` versus final train loss `0.4798` deserves qualitative validation review, but is not by itself a training failure.
- Two train records had tokenizer decoded-label exact-match differences due `.gov` spacing normalization. Since decoded labels still parsed as JSON and there was no truncation or label loss, this is not a blocker.
- A validation gold assistant sample already contains mojibake-like text around the name `Basho`. This appears to be present in the dataset target, not newly introduced by Candidate A. The next validation audit should quantify mojibake/encoding artifacts in gold and predictions.
- Flash Attention 2 remains broken and xformers fallback is used. This is accepted for now.
- The Candidate A adapter is a local model artifact and must not be committed to submitted package.

## Next Decision

Do not run Candidate B automatically.

The next stage should perform a validation-only Candidate A quality audit before the test set is touched. This audit should generate validation predictions, run deterministic format/readability/encoding checks, and do a stratified manual-quality review across domains and length buckets. Project review will then decide whether to:

- skip Candidate B and proceed to final test evaluation,
- request Candidate B,
- or fix a data/evaluation issue first.
