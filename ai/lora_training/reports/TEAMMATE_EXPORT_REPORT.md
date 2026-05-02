# Teammate Export Report

## Scope

- Split input directory: `ai/lora_training/data/splits`
- Export output directory: `ai/lora_training/data/teammate_exports`
- Metadata manifest: `ai/lora_training/data/teammate_exports\teammate_export_manifest.json`
- Report path: `ai/lora_training/reports/TEAMMATE_EXPORT_REPORT.md`
- Script SHA256: `160b1059a5a70dab37a67956e3a411bd308dfa8c3f9abd0ca1afc80e4a2e2189`
- Metadata manifest SHA256: `bcb11dd7104e524b7078708d53af75b787e47503558186b1b5d0bbe215d9b89d`

## Export Counts And Hashes

| File | Rows | Expected Rows | SHA256 |
| --- | --- | --- | --- |
| user_train.jsonl | 1162 | 1162 | 1f3b6ebc55dc5c6400e61a63bfe51a2eb17478e92888591228a85a6d739994d0 |
| assistant_train.jsonl | 1162 | 1162 | 043c73d00bc74a2ce0b55f7bd5b8d95edc9c946848cf786df3efb75f099ce61d |
| user_val.jsonl | 145 | 145 | ec0477036854f7601b92ce4e70bdcd4c76631c82ab096444bd1b5e6fea307258 |
| assistant_val.jsonl | 145 | 145 | d2f263f9508b9c0ce272e53ea98e60f0b84fc96d26e5e1ae2b26981072307663 |
| user_test.jsonl | 145 | 145 | 701984c0caa024050ef0a2c3103bafb04a319e4a6f03833ab02e13fb9cbd5883 |
| assistant_test.jsonl | 145 | 145 | bf7e697e101c47959fa900fec3b2dc53a1cdcc16df8f71cadb66d414128c89b4 |
| user_all.jsonl | 1452 | 1452 | 2d9a70b88906147a8d77c88f983ef9e5b2a3b20f5788926528d3c2c275a844c2 |
| assistant_all.jsonl | 1452 | 1452 | 283bd121bd834738f7b4ce10c2e7d53edf7b4f01352601e2f9c55c2b9f3fcefc |

## Source Split Hashes

| Input | Before SHA256 | After SHA256 |
| --- | --- | --- |
| train.jsonl | b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb | b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb |
| val.jsonl | a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be | a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be |
| test.jsonl | 6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f | 6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f |
| split_manifest.json | 42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19 | 42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19 |

## Source Parse Summary

| Split | Rows | Unique Stable Hashes | System Prompts Seen |
| --- | --- | --- | --- |
| train | 1162 | 1162 | 1 |
| val | 145 | 145 | 1 |
| test | 145 | 145 | 1 |

## Pairing Verification

| Scope | Counts Match | Shared Fields Match | Pair Index OK | Key Order OK | No Messages Field | Unique Pair IDs |
| --- | --- | --- | --- | --- | --- | --- |
| train | True | True | True | True | True | 1162 |
| val | True | True | True | True | True | 145 |
| test | True | True | True | True | True | 145 |
| all | True | True | True | True | True | 1452 |

## Safety Verification

| Check | Result |
| --- | --- |
| Source split hashes unchanged | True |
| All export order is train then val then test | True |
| No system prompt text appears in export text | True |
| Metadata manifest has no forbidden raw-text keys | True |
| No export row contains messages | True |

## Metadata Manifest Safety

- No forbidden raw-text manifest keys were found.

## Determinism

- The script writes rows in source split order and uses Worker 001 `record_id` values as `pair_id`.
- The script embeds no wall-clock timestamp in generated artifacts so reruns with unchanged inputs are stable.
- Worker 002 reran the script and compared 11 file hashes: deterministic rerun verification passed.

## Result

- All required export checks passed: `True`
