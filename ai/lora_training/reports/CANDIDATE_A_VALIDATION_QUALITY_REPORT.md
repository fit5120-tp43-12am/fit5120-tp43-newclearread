# Candidate A Validation Quality Report

Date/time: 2026-04-28T17:53:55+10:00

## Scope

- Evaluated Candidate A on `data/splits/val.jsonl` only.
- Did not use `data/splits/test.jsonl`.
- Did not run training.
- Prediction JSONL and metrics JSON are local artifacts and should not be committed without central-brain approval.

## Inputs And Local Artifacts

- Config: `ai/lora_training/configs/train_llama31_8b_qlora_candidate_a.example.yaml`
- Adapter: `ai/lora_training/models/adapters/full_candidate_a_3epoch`
- Validation data: `ai/lora_training/data/splits/val.jsonl`
- Validation SHA256: `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- Validation records: `145` expected `145`
- Predictions: `ai/lora_training/outputs/evaluation/candidate_a_validation/validation_predictions.jsonl`
- Metrics: `ai/lora_training/outputs/evaluation/candidate_a_validation/validation_metrics.json`

## Generation Timing

- Started: `2026-04-28T17:40:57+10:00`
- Finished: `2026-04-28T17:52:35+10:00`
- Elapsed: `11m 38s`
- Average seconds/example: `4.814`

## Deterministic Metrics

| Metric | Value |
| --- | --- |
| count | 145 |
| JSON parse rate | 145/145 (100.00%) |
| schema pass rate | 145/145 (100.00%) |
| exact key order rate | 145/145 (100.00%) |
| main_idea string rate | 145/145 (100.00%) |
| key_points list rate | 145/145 (100.00%) |
| exactly 4 key points rate | 145/145 (100.00%) |
| all key points strings rate | 145/145 (100.00%) |
| main_idea two-sentence rate | 144/145 (99.31%) |
| each key point one-sentence rate | 143/145 (98.62%) |
| empty-string rows | 0 |
| output too short / too long | 0 / 0 |
| avg main_idea words | 32.4 |
| avg key-point words | 16.67 |
| markdown/code-fence leakage | 0 |
| extra text outside JSON | 0 |
| refusal/meta-response phrases | 0 |
| prediction mojibake rows | 0 |
| gold mojibake rows | 0 |

Metric notes: sentence counts are approximate punctuation-based checks. Output too short means under 35 regex words across the parsed summary; too long means over 180 regex words.

## Domain Breakdown

| Domain | N | JSON Parse | Schema | Main 2 Sent | KPs 1 Sent | Pred Mojibake | Gold Mojibake | Too Short | Too Long |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| academic_book | 23 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_paper | 49 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| assignment_rubric | 8 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| gen_know | 13 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medlineplus | 23 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| public_service | 20 | 100.00% | 100.00% | 100.00% | 95.00% | 0 | 0 | 0 | 0 |
| tech_doc | 9 | 100.00% | 100.00% | 88.89% | 88.89% | 0 | 0 | 0 | 0 |

## Natural Length Bucket Breakdown

| Bucket | N | JSON Parse | Schema | Main 2 Sent | KPs 1 Sent | Pred Mojibake | Gold Mojibake | Too Short | Too Long |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| long | 19 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medium | 101 | 100.00% | 100.00% | 99.01% | 98.02% | 0 | 0 | 0 | 0 |
| short | 25 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |

## Domain X Natural Length Bucket Breakdown

| Domain / Bucket | N | JSON Parse | Schema | Main 2 Sent | KPs 1 Sent | Pred Mojibake | Gold Mojibake | Too Short | Too Long |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| academic_book / long | 2 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_book / medium | 15 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_book / short | 6 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_paper / long | 5 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_paper / medium | 35 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_paper / short | 9 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| assignment_rubric / long | 7 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| assignment_rubric / medium | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| gen_know / long | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| gen_know / medium | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| gen_know / short | 2 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medlineplus / long | 2 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medlineplus / medium | 18 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medlineplus / short | 3 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| public_service / long | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| public_service / medium | 15 | 100.00% | 100.00% | 100.00% | 93.33% | 0 | 0 | 0 | 0 |
| public_service / short | 4 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| tech_doc / long | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| tech_doc / medium | 7 | 100.00% | 100.00% | 85.71% | 85.71% | 0 | 0 | 0 | 0 |
| tech_doc / short | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |

## Encoding And Mojibake Audit

- Patterns scanned (Unicode escaped): `["\ufffd", "\u8252", "\u9225", "\u00c3", "\u00c2", "\u00e2\u20ac\u2122", "\u00e2\u20ac\u0153", "\u00e2\u20ac\u009d", "\u951f", "\u9479", "\u95b3", "\u8119", "\u8117", "\u8292\u9227\ue0fd\u5289", "\u8292\u9227\ue0e0?", "\u8292\u9227\ue0dd?", "\u9225\u6a9a", "\u57be", "\u59be\u6b5a"]`
- Prediction mojibake rows: `0`
- Gold assistant mojibake rows: `0`
- Prediction pattern counts: `{}`
- Gold pattern counts: `{}`

## Script-Selected Manual Review Candidates

The table below is the stratified candidate set selected by the script. Manual review used this set and added rows 17 and 98 because deterministic checks flagged sentence-count issues there.

| Row | Domain | Bucket | Record ID | Source File | Source Line | Schema | Prediction Preview |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | academic_book | long | academic_book:000040:9bfd170c1df7 | academic_book_v1.jsonl | 40 | pass | {"main_idea":"The text explains how managers use informal communication, writing, and discussion to do their jobs. It... |
| 20 | academic_book | short | academic_book:000025:72d97a0ed41d | academic_book_v1.jsonl | 25 | pass | {"main_idea":"This text explains bond journal entries and long-term liabilities. It also shows that bond interest can... |
| 57 | academic_paper | long | academic_paper:000167:c67e2698fedb | academic_paper_v1.jsonl | 167 | pass | {"main_idea":"The text studies how foreign curriculum experts help design primary school curriculum change in Lesotho... |
| 45 | academic_paper | short | academic_paper:000039:581692463132 | academic_paper_v1.jsonl | 39 | pass | {"main_idea":"The text explains why choosing the right location for maintenance stations is important. It says this i... |
| 2 | assignment_rubric | long | assignment_rubric:000025:7c7863351ba9 | assignment_rubric_v1.jsonl | 25 | pass | {"main_idea":"The text is an assignment brief for a research paper introduction on cloud cybersecurity. It asks for a... |
| 1 | assignment_rubric | medium | assignment_rubric:000002:f6d33a3c7474 | assignment_rubric_v1.jsonl | 2 | pass | {"main_idea":"The text is an assignment brief for a literature review on multimedia resources in mobile-assisted lang... |
| 144 | gen_know | long | gen_know:000107:51526f5445ca | gen_know_v1.jsonl | 107 | pass | {"main_idea":"This text gives an overview of Cibao International Airport in the Dominican Republic. It says the airpo... |
| 137 | gen_know | short | gen_know:000052:881b2393c988 | gen_know_v1.jsonl | 52 | pass | {"main_idea":"This text describes Cohoes Falls in New York and its history. It also explains why the falls were impor... |
| 114 | medlineplus | long | medlineplus:000072:c3f31e07ed28 | medlineplus_v1.jsonl | 72 | pass | {"main_idea":"This text explains respiratory syncytial virus, or RSV. It says RSV is common, usually causes mild symp... |
| 111 | medlineplus | short | medlineplus:000025:5c8b19412a43 | medlineplus_v1.jsonl | 25 | pass | {"main_idea":"This text explains what blood thinners are and why people use them. It also warns that they can cause b... |
| 95 | public_service | long | public_service:000040:e50bbabbf456 | public_service_v1.jsonl | 40 | pass | {"main_idea":"This text explains how to apply for a Florida marriage license and what documents and rules you need. I... |
| 97 | public_service | short | public_service:000056:c6b7f39c2694 | public_service_v1.jsonl | 56 | pass | {"main_idea":"This text explains how to contact ICE with tips, reports, and detention information. It also describes ... |
| 14 | tech_doc | long | tech_doc:000062:d49d5dc882d5 | tech_doc_v1.jsonl | 62 | pass | {"main_idea":"This text explains basic UNIX network programming in C. It shows how to make a simple client and server... |
| 9 | tech_doc | short | tech_doc:000004:71dc0280d49e | tech_doc_v1.jsonl | 4 | pass | {"main_idea":"The text explains how Python variables work in different scopes. It also shows how global and nonlocal ... |

## Manual Review

Reviewed 16 validation examples: at least 2 from each of the 7 domains, with short, medium, and long buckets represented. The review compared source metadata/short previews, gold assistant JSON, and Candidate A predictions without copying long source text into this Git-safe report.

Manual labels: `pass` 14, `minor_issue` 2, `major_issue` 0, `uncertain` 0.

| Row | Domain | Bucket | Label | Reason |
| --- | --- | --- | --- | --- |
| 1 | assignment_rubric | medium | pass | Faithfully summarizes the MALL literature-review assignment and rubric instead of following the embedded request. |
| 2 | assignment_rubric | long | pass | Correctly treats the cloud-cybersecurity prompt as an assignment brief and preserves major requirements. |
| 9 | tech_doc | short | pass | Accurate Python variable/scope summary with valid JSON and readable wording. |
| 14 | tech_doc | long | pass | Captures UNIX socket client/server concepts and related functions at an appropriate high level. |
| 17 | tech_doc | medium | pass | Good summary of the Python Hello World tutorial; sentence heuristic failed only because `Hello, World!` contains punctuation. |
| 20 | academic_book | short | pass | Faithful bond-accounting summary, including issuer viewpoint and IFRS/US GAAP distinction. |
| 21 | academic_book | long | pass | Preserves the management communication theme and the point that facts require interpretation. |
| 45 | academic_paper | short | pass | Faithfully summarizes maintenance-station location selection and modeling approaches. |
| 57 | academic_paper | long | pass | Covers Lesotho curriculum reform, foreign experts, and qualitative interview method without unsupported claims. |
| 95 | public_service | long | pass | Preserves Florida marriage-license documents, waiting/validity rules, and local-courthouse dependency at a useful level. |
| 97 | public_service | short | pass | Correctly distinguishes online ICE tips, anonymous tip line use, detention reporting, and detainee locator limits. |
| 98 | public_service | medium | minor_issue | Main summary is faithful, but the prediction copies a noisy fee detail into an awkward unsupported amount; avoid exact fees when source text is noisy. |
| 111 | medlineplus | short | pass | Preserves blood-thinner purpose, indications, types, bleeding warning, and need to follow directions. |
| 114 | medlineplus | long | pass | Preserves RSV spread, high-risk groups, lack of specific treatment, and prevention options in simple language. |
| 137 | gen_know | short | minor_issue | Overall Cohoes Falls summary is useful, but it slightly muddles attribution around the Mohawk name/history detail. |
| 144 | gen_know | long | pass | Accurate Cibao airport summary with location, traffic rank, main users/carriers, and expansion history. |

Manual review found no instruction-following failures, no refusal/meta behavior, no mojibake, and no broad domain or length-bucket quality collapse. The two minor issues were isolated factual/wording precision concerns, not format failures.

## Recommendation

Recommendation: `proceed_to_final_evaluation`.

Candidate A is ready for central-brain review and final test evaluation planning. Candidate B is not recommended at this point because validation format/schema metrics are excellent, sentence compliance is strong, all domains and length buckets are healthy, and manual review found no major faithfulness or instruction-following issue. The final evaluation should still watch public-service examples for copied or malformed exact numeric details, especially fees and time windows.
