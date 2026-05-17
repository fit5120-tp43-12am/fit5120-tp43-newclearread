# Stage 001 Profile Source Distributions And Create Data Splits

Date/time: 2026-04-28 13:20:44 +10:00

## Scope

- Stage reference: `Stage 001 profile and split`
- Source dataset path: `ai/data_preparation/final_lora_data/outputs/final_dataset_v1_training_system_clean/accepted`
- Training workspace: `ai/lora_training`
- Team repo: `<team-repo-root>`

## Source File Hashes

| File | SHA256 |
|---|---|
| `assignment_rubric_v1.jsonl` | `fd8367dd2644f126c22aa19164c0a6dfcb364e7046c0e85b2e10f02c696827c1` |
| `tech_doc_v1.jsonl` | `3377d24a4cfbd10d2cc5b5598dcab760c8bdb25f82d179434565dbbd24f1527d` |
| `academic_book_v1.jsonl` | `afc607d744d164ba8a6872e77d6e7ab388c24e0ccdcaa27e0989b8d8c12c54da` |
| `academic_paper_v1.jsonl` | `495037cbadba288fc84f62d45ad93ce1af68cfab7d6826d88eb8e26f8649783f` |
| `public_service_v1.jsonl` | `fc4d4b6a7aff3180b15c106552127b920c6a171fde47b1c2e7df6f7e13234c0f` |
| `medlineplus_v1.jsonl` | `b973097a9f3389ee0b30c84f528d82ea7d685c7c40fd25b0ce74301a7b423a37` |
| `gen_know_v1.jsonl` | `1e13393d4e36d08bd5708060191467d13694d5d5af459d425b2ad5ea89532fdc` |
| `all_v1.jsonl` | `c82097c07054198a791297998786b18a3d202d78684fcef03dbe723659c0fea2` |

## Script And Outputs

- Script: `ai/lora_training/scripts/create_stratified_splits.py`
- Source profile JSON: `ai/lora_training/reports/source_distribution_profile.json`
- Source profile markdown: `ai/lora_training/reports/SOURCE_DISTRIBUTION_PROFILE.md`
- Train split: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/train.jsonl`
- Validation split: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/val.jsonl`
- Test split: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/test.jsonl`
- Smoke split: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/smoke_test_10.jsonl`
- Split manifest: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/split_manifest.json`
- Split report: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/SPLIT_REPORT.md`

## Output Hashes

| Output | SHA256 |
|---|---|
| script | `74f07595038100f222ebcf1a9da0a0086994846e84bc6df987cc8bdf255fb26c` |
| profile_json | `fa1ac3bcc29c15a557ab92c077f744af7986a2ddff68c5cfeb4c77c91e0ac14a` |
| profile_md | `3bb66738ef335720d07fc61f09798ec1b03cc64393e5a134b03caa4a174d953a` |
| train | `b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb` |
| val | `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be` |
| test | `6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f` |
| smoke | `8f51d083e8fafae143ec146c0155f85dc23a5cfdaf931a04092e7f8543d2d3a8` |
| manifest | `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19` |
| split_report | `e88a218192f6f78f0db08418768a745591ed79a96d07e6750a0f44206dd9aaa6` |

## Split Counts

| Split | Count |
|---|---:|
| train | 1162 |
| val | 145 |
| test | 145 |

## Domain Count Verification

| Domain | Train | Val | Test |
|---|---:|---:|---:|
| assignment_rubric | 67 | 8 | 8 |
| tech_doc | 71 | 9 | 9 |
| academic_book | 187 | 23 | 23 |
| academic_paper | 388 | 49 | 49 |
| public_service | 158 | 20 | 20 |
| medlineplus | 184 | 23 | 23 |
| gen_know | 107 | 13 | 13 |

## Length Bucket Verification

| Split | Short | Medium | Long |
|---|---:|---:|---:|
| source | 241 | 1018 | 193 |
| train | 191 | 816 | 155 |
| val | 25 | 101 | 19 |
| test | 25 | 101 | 19 |

The documented word-count regex is `[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*`. With this regex, the source medium bucket is 1018 records, 70.11%, which confirms the expected concentration around 70.18%. The source median user word count is 622, close to the expected around 623, and `academic_paper` is 486 records, 33.47%.

## Smoke Set Selection Summary

- Smoke set has 10 records.
- All smoke records are from train.
- Domains represented: medlineplus 2, public_service 2, academic_paper 2, academic_book 1, tech_doc 1, assignment_rubric 1, gen_know 1.
- Buckets represented: short, medium, long.
- Selected record IDs/hashes are listed in `SPLIT_REPORT.md`.

## Verification Results

- Train count 1162: pass.
- Validation count 145: pass.
- Test count 145: pass.
- Total unique train/val/test hashes 1452: pass.
- Train/val/test overlap: none.
- Per-domain split counts match the target table exactly: pass.
- Manifest entries 1452: pass.
- Manifest contains metadata only and no `messages`, `system`, `user`, `assistant`, or `content` fields: pass.
- Source file hashes after generation match the hashes recorded in the profile: pass.
- Script determinism: pass; rerunning the script produced identical SHA256 hashes for script, profile reports, split JSONL files, manifest, and split report.

## Git

- Branch: `feature/ai-llama-lora-training`
- Primary artifact commit: `1105b245edb419fe3830a683c850f4a3461a9457`
- Primary commit message: `feat(ai): add stratified split profiling workflow`
- Primary push result: pushed to `origin/feature/ai-llama-lora-training` (`c017273..1105b24`).
- package-ready files mirrored in primary commit:
  - `ai\scripts\create_stratified_splits.py`
  - `ai\reports\source_distribution_profile.json`
  - `ai\reports\SOURCE_DISTRIBUTION_PROFILE.md`
  - `ai\reports\SPLIT_REPORT.md`
  - `ai\reports\split_manifest.json`
- Full split JSONL files were not copied into the team repo.

## Blockers Or Deviations

- No blockers.
- No allocation deviations were needed; largest-remainder allocations were feasible without adjustment.
- `rg` was unavailable in this environment with an access denied error, so PowerShell native file enumeration was used.
- A docs-only follow-up commit is expected to mirror this stage log to the team repo, matching the Stage 000 pattern for post-push logs.

## Recommendation

Project review should pass Stage 001. Stage 002 can proceed with teammate exports after model-selection review.
