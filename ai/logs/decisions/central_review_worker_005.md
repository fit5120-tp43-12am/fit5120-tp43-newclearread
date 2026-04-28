# Central-Brain Review: Worker 005 Llama Smoke Test

Date/time: 2026-04-28

## Decision

Result: pass.

Worker 005 successfully ran the first real Llama-3.1-8B-Instruct QLoRA smoke training test on the approved 10-record smoke split. The run completed without OOM, saved a local LoRA adapter, and produced valid-schema inference outputs on 3 of 3 smoke examples.

## Evidence Reviewed

Local files reviewed:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\logs\smoke_test_001.md
C:\Users\Aufb\Desktop\fit5120\iteration1\training\logs\decisions\worker_005_llama_smoke_test.md
C:\Users\Aufb\Desktop\fit5120\iteration1\training\reports\SMOKE_TRAINING_RUN_REPORT.md
```

Key reported result:

- model: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- smoke data SHA256: `8F51D083E8FAFAE143EC146C0155F85DC23A5CFDAF931A04092E7F8543D2D3A8`
- split manifest SHA256: `42BFE9974C31E74B98B45D45DAA792F8582D517541E153439B510E9A9B307F19`
- final train loss: `0.5587`
- final step loss: `0.02816`
- trainer runtime: `87.37` seconds
- script training elapsed runtime: `89.61` seconds
- final callback average: `4.368` seconds per step
- inference schema pass: `3/3`

## Independent Verification

Central-brain checks confirmed the smoke split and manifest hashes:

```text
smoke_test_10.jsonl: 8F51D083E8FAFAE143EC146C0155F85DC23A5CFDAF931A04092E7F8543D2D3A8
split_manifest.json: 42BFE9974C31E74B98B45D45DAA792F8582D517541E153439B510E9A9B307F19
```

Central-brain verified the local adapter directory exists:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\models\adapters\smoke_llama31_8b_qlora
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

Central-brain independently reran inference in WSL env `clearread-llama-lora`:

```bash
python scripts/run_inference_check.py --config configs/smoke_llama31_8b_qlora.yaml --num-examples 3
```

Result:

```text
status: ok
checked: 3
schema_pass: 3
```

This rerun loaded the base model and saved adapter, used the known xformers fallback, and passed the schema check.

## Git Verification

Team repo:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\code\fit5120-tp43-newclearread
```

Central-brain verified:

- branch: `feature/ai-llama-lora-training`
- local HEAD: `919fc29575075e0fd60664ae1f6e7792de2f377c`
- upstream HEAD: `919fc29575075e0fd60664ae1f6e7792de2f377c`
- worktree was clean before central-brain follow-up files
- latest commits:
  - `919fc29 docs(ai): record worker 005 smoke result`
  - `6e6b7bf docs(ai): record llama smoke test result`

Git safety checks returned no tracked raw data or model binary artifacts:

```text
git ls-files 'ai/**/*.jsonl' -> empty
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin' -> empty
```

## Notes

- The worker decision log still says the follow-up Git commit/push was pending at that log revision. This is not a blocker because the actual Git state confirms the follow-up commit exists and HEAD equals upstream at `919fc29575075e0fd60664ae1f6e7792de2f377c`.
- Flash Attention 2 remains broken in this environment, but Unsloth successfully uses xformers fallback. This is accepted for now.
- Hugging Face CLI is still not logged in. The successful smoke run used the public Unsloth model path, so this is not a blocker unless the official gated Meta fallback becomes necessary.
- The saved smoke adapter is a local model artifact and must not be committed to normal Git.

## Next Decision

Worker 005 is approved. The next worker should proceed to Worker 006: full training Candidate A, with a full train/validation tokenization preflight before starting the 3-epoch run.
