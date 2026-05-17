# Split Report

Split method: deterministic approximate joint stratification over `domain x natural_length_bucket`.

Validation and test first match the accepted per-domain targets, then largest-remainder rounding preserves each domain's natural short/medium/long distribution as closely as integer counts allow. Within each domain-bucket cell, held-out records are selected evenly across records sorted by user word count, stable hash, and source line.

Seed recorded for reproducibility: `5120`. No random draw is used in the final selection.

## Split Counts

| Split | Count | Percent of Source |
| --- | --- | --- |
| train | 1162 | 80.03% |
| val | 145 | 9.99% |
| test | 145 | 9.99% |

## Domain Count Verification

| Domain | Source | Train | Val | Test |
| --- | --- | --- | --- | --- |
| assignment_rubric | 83 | 67 | 8 | 8 |
| tech_doc | 89 | 71 | 9 | 9 |
| academic_book | 233 | 187 | 23 | 23 |
| academic_paper | 486 | 388 | 49 | 49 |
| public_service | 198 | 158 | 20 | 20 |
| medlineplus | 230 | 184 | 23 | 23 |
| gen_know | 133 | 107 | 13 | 13 |

## Overall Natural Length Bucket Counts

| Bucket | Source | Source % | Train | Val | Test |
| --- | --- | --- | --- | --- | --- |
| short | 241 | 16.60% | 191 | 25 | 25 |
| medium | 1018 | 70.11% | 816 | 101 | 101 |
| long | 193 | 13.29% | 155 | 19 | 19 |

## Source Cross-Tab

| Domain | Short | Medium | Long | Total |
| --- | --- | --- | --- | --- |
| assignment_rubric | 0 | 15 | 68 | 83 |
| tech_doc | 11 | 69 | 9 | 89 |
| academic_book | 59 | 155 | 19 | 233 |
| academic_paper | 89 | 348 | 49 | 486 |
| public_service | 34 | 152 | 12 | 198 |
| medlineplus | 32 | 175 | 23 | 230 |
| gen_know | 16 | 104 | 13 | 133 |

## Train Cross-Tab

| Domain | Short | Medium | Long | Total |
| --- | --- | --- | --- | --- |
| assignment_rubric | 0 | 13 | 54 | 67 |
| tech_doc | 9 | 55 | 7 | 71 |
| academic_book | 47 | 125 | 15 | 187 |
| academic_paper | 71 | 278 | 39 | 388 |
| public_service | 26 | 122 | 10 | 158 |
| medlineplus | 26 | 139 | 19 | 184 |
| gen_know | 12 | 84 | 11 | 107 |

## Validation Cross-Tab

| Domain | Short | Medium | Long | Total |
| --- | --- | --- | --- | --- |
| assignment_rubric | 0 | 1 | 7 | 8 |
| tech_doc | 1 | 7 | 1 | 9 |
| academic_book | 6 | 15 | 2 | 23 |
| academic_paper | 9 | 35 | 5 | 49 |
| public_service | 4 | 15 | 1 | 20 |
| medlineplus | 3 | 18 | 2 | 23 |
| gen_know | 2 | 10 | 1 | 13 |

## Test Cross-Tab

| Domain | Short | Medium | Long | Total |
| --- | --- | --- | --- | --- |
| assignment_rubric | 0 | 1 | 7 | 8 |
| tech_doc | 1 | 7 | 1 | 9 |
| academic_book | 6 | 15 | 2 | 23 |
| academic_paper | 9 | 35 | 5 | 49 |
| public_service | 4 | 15 | 1 | 20 |
| medlineplus | 3 | 18 | 2 | 23 |
| gen_know | 2 | 10 | 1 | 13 |

## Val/Test Bucket Allocation By Domain

| Domain | Bucket | Source | Val | Test | Train Remainder |
| --- | --- | --- | --- | --- | --- |
| assignment_rubric | short | 0 | 0 | 0 | 0 |
| assignment_rubric | medium | 15 | 1 | 1 | 13 |
| assignment_rubric | long | 68 | 7 | 7 | 54 |
| tech_doc | short | 11 | 1 | 1 | 9 |
| tech_doc | medium | 69 | 7 | 7 | 55 |
| tech_doc | long | 9 | 1 | 1 | 7 |
| academic_book | short | 59 | 6 | 6 | 47 |
| academic_book | medium | 155 | 15 | 15 | 125 |
| academic_book | long | 19 | 2 | 2 | 15 |
| academic_paper | short | 89 | 9 | 9 | 71 |
| academic_paper | medium | 348 | 35 | 35 | 278 |
| academic_paper | long | 49 | 5 | 5 | 39 |
| public_service | short | 34 | 4 | 4 | 26 |
| public_service | medium | 152 | 15 | 15 | 122 |
| public_service | long | 12 | 1 | 1 | 10 |
| medlineplus | short | 32 | 3 | 3 | 26 |
| medlineplus | medium | 175 | 18 | 18 | 139 |
| medlineplus | long | 23 | 2 | 2 | 19 |
| gen_know | short | 16 | 2 | 2 | 12 |
| gen_know | medium | 104 | 10 | 10 | 84 |
| gen_know | long | 13 | 1 | 1 | 11 |

## Allocation Deviations

- None. Largest-remainder allocations were feasible without adjustment.

## Smoke Set Selection

The smoke set contains 10 records, all selected from train only.

| # | Domain | Bucket | User Words | Source File | Line | Record ID | Stable Hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | medlineplus | short | 327 | medlineplus_v1.jsonl | 227 | medlineplus:000227:db32be2813ba | db32be2813baa2d07b962bd27b567b8713c63d6e4556200e91c249ef9815c599 |
| 2 | medlineplus | medium | 642 | medlineplus_v1.jsonl | 17 | medlineplus:000017:71c1ad8ed8ef | 71c1ad8ed8eff7f3cca6d21ce9325fd5041e668f7811122d377837c0acaef1fc |
| 3 | public_service | medium | 548 | public_service_v1.jsonl | 142 | public_service:000142:220899075124 | 2208990751243c8869e683e0f355a682fdc1db15a1a1831c8f47834461d023e3 |
| 4 | public_service | long | 883 | public_service_v1.jsonl | 67 | public_service:000067:99351db3597c | 99351db3597cc992c5a661afa760edef2933faf7800826db1aa7c23a51ac6a63 |
| 5 | academic_paper | short | 363 | academic_paper_v1.jsonl | 205 | academic_paper:000205:7016ca3e0d34 | 7016ca3e0d342bf5ca534a205ef4cce7d1dc7f7aff39eae838b0ae330ff39084 |
| 6 | academic_paper | medium | 626 | academic_paper_v1.jsonl | 415 | academic_paper:000415:da5f73ee1ab8 | da5f73ee1ab8a1aff1e9126c425660b634490400792e7460f8ab2b50237c48c3 |
| 7 | academic_book | medium | 596 | academic_book_v1.jsonl | 145 | academic_book:000145:e4c072a4b19b | e4c072a4b19bd660ccc1ebf411a1f1b4f2e4980af8455137ab9c8fcaf0240dc3 |
| 8 | tech_doc | medium | 660 | tech_doc_v1.jsonl | 26 | tech_doc:000026:0505970f9ad0 | 0505970f9ad051f86140a826c6c2b86b5801a1524727fdaa008efa046ebfbe5f |
| 9 | assignment_rubric | long | 1029 | assignment_rubric_v1.jsonl | 48 | assignment_rubric:000048:da6011d79977 | da6011d79977102e4250879741c786c8b9628a2a455ecccb389160393a77bbe2 |
| 10 | gen_know | medium | 655 | gen_know_v1.jsonl | 125 | gen_know:000125:732b3c435b61 | 732b3c435b61f160d7d3b1568d1bd84962d55fa9e7be5f1f9a7a07cf068599c4 |

Smoke selection notes:

- No fallback was needed; preferred domain/bucket composition was available.

## Verification

| Check | Result |
| --- | --- |
| train_count_is_1162 | True |
| val_count_is_145 | True |
| test_count_is_145 | True |
| total_unique_train_val_test_hashes_is_1452 | True |
| no_train_val_overlap | True |
| no_train_test_overlap | True |
| no_val_test_overlap | True |
| per_domain_counts_match_targets | True |
| smoke_count_is_10 | True |
| smoke_records_all_from_train | True |
| manifest_entry_count_is_1452 | True |
| manifest_has_no_message_text_fields | True |
| source_record_count_is_1452 | True |
| all_checks_passed | True |

## Output File Hashes

| Output | SHA256 |
| --- | --- |
| reports/source_distribution_profile.json | fa1ac3bcc29c15a557ab92c077f744af7986a2ddff68c5cfeb4c77c91e0ac14a |
| reports/SOURCE_DISTRIBUTION_PROFILE.md | 3bb66738ef335720d07fc61f09798ec1b03cc64393e5a134b03caa4a174d953a |
| <external-local-raw-8b-training-workspace-not-in-git>/data/splits/train.jsonl | b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb |
| <external-local-raw-8b-training-workspace-not-in-git>/data/splits/val.jsonl | a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be |
| <external-local-raw-8b-training-workspace-not-in-git>/data/splits/test.jsonl | 6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f |
| <external-local-raw-8b-training-workspace-not-in-git>/data/splits/smoke_test_10.jsonl | 8f51d083e8fafae143ec146c0155f85dc23a5cfdaf931a04092e7f8543d2d3a8 |
| <external-local-raw-8b-training-workspace-not-in-git>/data/splits/split_manifest.json | 42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19 |
