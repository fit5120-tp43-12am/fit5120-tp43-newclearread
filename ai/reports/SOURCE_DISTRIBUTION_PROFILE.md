# Source Distribution Profile

Source dataset: `C:\Users\Aufb\Desktop\fit5120\iteration1\data\final_lora_data\outputs\final_dataset_v1_training_system_clean\accepted`

Total records: **1452**

Word counts use this documented regex:

`[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*`

Counts English alphanumeric tokens, including tokens with internal apostrophes or hyphens.

## Domain Distribution

| Domain | Count | Percent |
| --- | --- | --- |
| assignment_rubric | 83 | 5.72% |
| tech_doc | 89 | 6.13% |
| academic_book | 233 | 16.05% |
| academic_paper | 486 | 33.47% |
| public_service | 198 | 13.64% |
| medlineplus | 230 | 15.84% |
| gen_know | 133 | 9.16% |

## Natural Length Bucket Distribution

| Bucket | Count | Percent |
| --- | --- | --- |
| short | 241 | 16.60% |
| medium | 1018 | 70.11% |
| long | 193 | 13.29% |

## Domain x Natural Length Bucket Cross-Tab

| Domain | Short | Medium | Long | Total |
| --- | --- | --- | --- | --- |
| assignment_rubric | 0 | 15 | 68 | 83 |
| tech_doc | 11 | 69 | 9 | 89 |
| academic_book | 59 | 155 | 19 | 233 |
| academic_paper | 89 | 348 | 49 | 486 |
| public_service | 34 | 152 | 12 | 198 |
| medlineplus | 32 | 175 | 23 | 230 |
| gen_know | 16 | 104 | 13 | 133 |

## 100-Word User Word Count Histogram

| Bin | Count | Percent |
| --- | --- | --- |
| <=300 | 48 | 3.31% |
| 301-400 | 193 | 13.29% |
| 401-500 | 96 | 6.61% |
| 501-600 | 242 | 16.67% |
| 601-700 | 532 | 36.64% |
| 701-800 | 148 | 10.19% |
| 801-900 | 44 | 3.03% |
| 901-1000 | 83 | 5.72% |
| 1001-1100 | 49 | 3.37% |
| 1101-1200 | 16 | 1.10% |
| >1200 | 1 | 0.07% |

## Overall User Word Count Stats

| Metric | Value |
| --- | --- |
| min | 221 |
| p10 | 358 |
| p25 | 511 |
| p33 | 562 |
| p50 | 622 |
| p67 | 661 |
| p75 | 698 |
| p90 | 905 |
| p95 | 989.9 |
| p99 | 1106.92 |
| max | 1209 |
| mean | 618.62 |

## Per-Domain User Word Count Stats

| Domain | Min | P10 | P25 | P33 | P50 | P67 | P75 | P90 | P95 | P99 | Max | Mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| assignment_rubric | 493 | 763.8 | 855 | 921.42 | 987 | 1050 | 1081.5 | 1146.2 | 1170.7 | 1198.34 | 1209 | 964.81 |
| tech_doc | 245 | 378 | 509 | 574.08 | 657 | 680.92 | 691 | 789.4 | 958.6 | 1055.48 | 1103 | 625.56 |
| academic_book | 253 | 344.2 | 386 | 518 | 570 | 629.88 | 695 | 706.8 | 874.4 | 996.36 | 1002 | 560.65 |
| academic_paper | 275 | 364 | 605.25 | 616 | 624 | 634 | 643 | 823 | 974.5 | 1035.15 | 1117 | 614.87 |
| public_service | 221 | 316.1 | 458.5 | 482.02 | 529 | 596.99 | 654.25 | 725.2 | 813.15 | 921.12 | 993 | 541.02 |
| medlineplus | 255 | 358.8 | 516.25 | 557.71 | 635 | 701.86 | 741.75 | 798 | 912.75 | 999.2 | 1143 | 620.3 |
| gen_know | 267 | 384.8 | 521 | 562.56 | 653 | 692.44 | 714 | 798.2 | 978.8 | 1029.68 | 1071 | 625.83 |

## Assistant Word Count Summary

| Metric | Value |
| --- | --- |
| min | 64 |
| p10 | 82 |
| p25 | 89 |
| p33 | 92 |
| p50 | 98 |
| p67 | 104 |
| p75 | 106 |
| p90 | 114 |
| p95 | 119 |
| p99 | 132 |
| max | 156 |
| mean | 98.35 |

## Role-Order Validation

- Expected roles: `system / user / assistant`
- Valid records: `1452`
- Invalid records: `0`

## Source File Counts And Hashes

| File | Line Count | Bytes | SHA256 | Used For Split |
| --- | --- | --- | --- | --- |
| assignment_rubric_v1.jsonl | 83 | 780010 | fd8367dd2644f126c22aa19164c0a6dfcb364e7046c0e85b2e10f02c696827c1 | True |
| tech_doc_v1.jsonl | 89 | 541469 | 3377d24a4cfbd10d2cc5b5598dcab760c8bdb25f82d179434565dbbd24f1527d | True |
| academic_book_v1.jsonl | 233 | 1392288 | afc607d744d164ba8a6872e77d6e7ab388c24e0ccdcaa27e0989b8d8c12c54da | True |
| academic_paper_v1.jsonl | 486 | 3211220 | 495037cbadba288fc84f62d45ad93ce1af68cfab7d6826d88eb8e26f8649783f | True |
| public_service_v1.jsonl | 198 | 1132773 | fc4d4b6a7aff3180b15c106552127b920c6a171fde47b1c2e7df6f7e13234c0f | True |
| medlineplus_v1.jsonl | 230 | 1427160 | b973097a9f3389ee0b30c84f528d82ea7d685c7c40fd25b0ce74301a7b423a37 | True |
| gen_know_v1.jsonl | 133 | 847140 | 1e13393d4e36d08bd5708060191467d13694d5d5af459d425b2ad5ea89532fdc | True |
| all_v1.jsonl | 1452 | 9332060 | c82097c07054198a791297998786b18a3d202d78684fcef03dbe723659c0fea2 | False |

## Known Fact Checks

| Check | Value |
| --- | --- |
| total_records_is_1452 | True |
| medium_401_800_count | 1018 |
| medium_401_800_percent | 70.11 |
| median_user_word_count | 622 |
| academic_paper_count | 486 |
| academic_paper_percent | 33.47 |
