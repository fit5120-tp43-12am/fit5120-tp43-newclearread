# Stage 002 Teammate User And Assistant Exports

Date/time: 2026-04-28 13:41:54 +10:00

## Scope

- Stage reference: `Stage 002 teammate export`
- Training workspace: `ai/lora_training`
- Team repo: `<team-repo-root>`
- Required branch: `feature/ai-llama-lora-training`

## Approved Inputs

| Input | Pre-run SHA256 | Post-run SHA256 |
|---|---|---|
| `data\splits\train.jsonl` | `b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb` | `b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb` |
| `data\splits\val.jsonl` | `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be` | `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be` |
| `data\splits\test.jsonl` | `6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f` | `6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f` |
| `data\splits\split_manifest.json` | `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19` | `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19` |

Source split files were unchanged.

## Script

- Path: `ai/lora_training/scripts/create_teammate_exports.py`
- SHA256: `80da172dace81865844c9df277908a04ad929b5bca3bada353029e189f5cbb09`
- Stable hash method: `sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()`
- Pair id source: Stage 001 `record_id` from `split_manifest.json`.

## Export Outputs

| Export | Rows | SHA256 |
|---|---:|---|
| `data\teammate_exports\user_train.jsonl` | 1162 | `1f3b6ebc55dc5c6400e61a63bfe51a2eb17478e92888591228a85a6d739994d0` |
| `data\teammate_exports\assistant_train.jsonl` | 1162 | `043c73d00bc74a2ce0b55f7bd5b8d95edc9c946848cf786df3efb75f099ce61d` |
| `data\teammate_exports\user_val.jsonl` | 145 | `ec0477036854f7601b92ce4e70bdcd4c76631c82ab096444bd1b5e6fea307258` |
| `data\teammate_exports\assistant_val.jsonl` | 145 | `d2f263f9508b9c0ce272e53ea98e60f0b84fc96d26e5e1ae2b26981072307663` |
| `data\teammate_exports\user_test.jsonl` | 145 | `701984c0caa024050ef0a2c3103bafb04a319e4a6f03833ab02e13fb9cbd5883` |
| `data\teammate_exports\assistant_test.jsonl` | 145 | `bf7e697e101c47959fa900fec3b2dc53a1cdcc16df8f71cadb66d414128c89b4` |
| `data\teammate_exports\user_all.jsonl` | 1452 | `2d9a70b88906147a8d77c88f983ef9e5b2a3b20f5788926528d3c2c275a844c2` |
| `data\teammate_exports\assistant_all.jsonl` | 1452 | `283bd121bd834738f7b4ce10c2e7d53edf7b4f01352601e2f9c55c2b9f3fcefc` |

## Metadata And Report Outputs

| Output | SHA256 |
|---|---|
| `data\teammate_exports\teammate_export_manifest.json` | `bcb11dd7104e524b7078708d53af75b787e47503558186b1b5d0bbe215d9b89d` |
| `reports\TEAMMATE_EXPORT_REPORT.md` | `22842676ce83a7be5ad97e97c27c35da3933f65e7465b62f43f39b6d7fba9eeb` |

## Verification Results

- Train export count: pass, user 1162 and assistant 1162.
- Validation export count: pass, user 145 and assistant 145.
- Test export count: pass, user 145 and assistant 145.
- All export count: pass, user 1452 and assistant 1452.
- Pair alignment: pass. For train, validation, test, and all exports, `pair_index`, `pair_id`, `record_id`, `stable_hash`, `split`, `domain`, `source_file`, `source_line`, and `natural_length_bucket` match row by row.
- Row shape: pass. User and assistant rows use the required key order.
- Source text extraction: pass. User `text` equals source role `user`; assistant `text` equals source role `assistant`.
- No system prompt in export text: pass. Exact system prompt text was not found in any exported user or assistant `text`.
- No `messages` field in exports: pass.
- All export ordering: pass. `user_all.jsonl` and `assistant_all.jsonl` contain train rows, then validation rows, then test rows; smoke rows were not appended as a duplicate source.
- Metadata manifest safety: pass. `teammate_export_manifest.json` contains no raw dataset text fields named `text`, `messages`, `system`, `user`, `assistant`, or `content`.
- Determinism: pass. Rerunning `py -3 scripts\create_teammate_exports.py` changed none of the 11 checked files.

## Git

- Branch before repo-side changes: `feature/ai-llama-lora-training`
- Branch status before repo-side changes: clean and aligned with `origin/feature/ai-llama-lora-training` at `e720eaa6661cdaf4e04fc3819a68e405250b61f6`.
- Primary commit: `704225f9d45e0e6f75f71b6d74c930500fd9ed8f` (`feat(ai): add teammate export workflow`).
- Primary push result: pushed to `origin/feature/ai-llama-lora-training` (`e720eaa..704225f`).
- Follow-up docs/log commit: `b5177955352bbd2239267179eea5a4a62c5f4c8f` (`docs(ai): record stage 002 teammate export result`).
- Follow-up push result: pushed to `origin/feature/ai-llama-lora-training` (`704225f..b517795`).
- `git ls-files 'ai/**/*.jsonl'` before repo-side changes returned no tracked JSONL files.

## Blockers Or Deviations

- No task blockers.
- `rg` was unavailable in this environment with an access denied error, so PowerShell and Python were used for file inspection and verification.
- A follow-up docs/log commit is used after the primary Git commit so this log can record the actual commit hash and push result.

## Recommendation

Project review should pass Stage 002. package-ready files were mirrored, committed, and pushed, and no `ai/**/*.jsonl` files are tracked.
