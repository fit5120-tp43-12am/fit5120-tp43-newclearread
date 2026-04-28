# Final Test Evaluation Candidate A Report

Date/time: 2026-04-28T18:29:42+10:00

## Scope

- Evaluated Candidate A on `data/splits/test.jsonl` only after central-brain approval.
- Did not run training, tune parameters, change decoding settings, or run Candidate B.
- Prediction JSONL and metrics JSON are local artifacts and should not be committed without central-brain approval.

## Inputs And Local Artifacts

- Config: `/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training/configs/train_llama31_8b_qlora_candidate_a.yaml`
- Adapter: `/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training/models/adapters/full_candidate_a_3epoch`
- Test data: `/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training/data/splits/test.jsonl`
- Test SHA256: `6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- Test records: `145` expected `145`
- Predictions: `/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training/outputs/evaluation/candidate_a_test/test_predictions.jsonl`
- Metrics: `/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training/outputs/evaluation/candidate_a_test/test_metrics.json`

## Generation Timing

- Started: `2026-04-28T18:17:52+10:00`
- Finished: `2026-04-28T18:29:42+10:00`
- Elapsed: `11m 50s`
- Average seconds/example: `4.899`

## Deterministic Metrics

| Metric | Value |
| --- | --- |
| count | 145 |
| JSON parse rate | 145/145 (100.00%) |
| schema pass rate | 144/145 (99.31%) |
| exact key order rate | 145/145 (100.00%) |
| main_idea string rate | 145/145 (100.00%) |
| key_points list rate | 145/145 (100.00%) |
| exactly 4 key points rate | 144/145 (99.31%) |
| all key points strings rate | 145/145 (100.00%) |
| main_idea two-sentence rate | 144/145 (99.31%) |
| each key point one-sentence rate | 144/145 (99.31%) |
| empty-string rows | 0 |
| output too short / too long | 0 / 0 |
| avg main_idea words | 33.02 |
| avg key-point words | 16.8 |
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
| academic_paper | 49 | 100.00% | 97.96% | 97.96% | 97.96% | 0 | 0 | 0 | 0 |
| assignment_rubric | 8 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| gen_know | 13 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medlineplus | 23 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| public_service | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| tech_doc | 9 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |

## Natural Length Bucket Breakdown

| Bucket | N | JSON Parse | Schema | Main 2 Sent | KPs 1 Sent | Pred Mojibake | Gold Mojibake | Too Short | Too Long |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| long | 19 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medium | 101 | 100.00% | 99.01% | 100.00% | 99.01% | 0 | 0 | 0 | 0 |
| short | 25 | 100.00% | 100.00% | 96.00% | 100.00% | 0 | 0 | 0 | 0 |

## Domain X Natural Length Bucket Breakdown

| Domain / Bucket | N | JSON Parse | Schema | Main 2 Sent | KPs 1 Sent | Pred Mojibake | Gold Mojibake | Too Short | Too Long |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| academic_book / long | 2 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_book / medium | 15 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_book / short | 6 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_paper / long | 5 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| academic_paper / medium | 35 | 100.00% | 97.14% | 100.00% | 97.14% | 0 | 0 | 0 | 0 |
| academic_paper / short | 9 | 100.00% | 100.00% | 88.89% | 100.00% | 0 | 0 | 0 | 0 |
| assignment_rubric / long | 7 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| assignment_rubric / medium | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| gen_know / long | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| gen_know / medium | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| gen_know / short | 2 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medlineplus / long | 2 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medlineplus / medium | 18 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| medlineplus / short | 3 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| public_service / long | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| public_service / medium | 15 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| public_service / short | 4 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| tech_doc / long | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| tech_doc / medium | 7 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |
| tech_doc / short | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0 | 0 | 0 |

## Encoding And Mojibake Audit

- Patterns scanned (Unicode escaped): `["\ufffd", "\u8252", "\u9225", "\u00c3", "\u00c2", "\u00e2\u20ac\u2122", "\u00e2\u20ac\u0153", "\u00e2\u20ac\u009d", "\u951f", "\u9479", "\u95b3", "\u8119", "\u8117", "\u8292\u9227\ue0fd\u5289", "\u8292\u9227\ue0e0?", "\u8292\u9227\ue0dd?", "\u9225\u6a9a", "\u57be", "\u59be\u6b5a"]`
- Prediction mojibake rows: `0`
- Gold assistant mojibake rows: `0`
- Prediction pattern counts: `{}`
- Gold pattern counts: `{}`

## Script-Selected Manual Review Candidates

The table below is the stratified candidate set selected by the script. It includes at least 2 examples from each domain where available, plus deterministic failures and required focus areas when present.

| Row | Domain | Bucket | Record ID | Source File | Source Line | Schema | Prediction Preview |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 66 | academic_paper | short | academic_paper:000208:4806781af9e9 | academic_paper_v1.jsonl | 208 | pass | {"main_idea":"The text explains why strong promoters are needed for gene expression control in microbes. It says a ne... |
| 87 | academic_paper | medium | academic_paper:000458:8541ac16b79f | academic_paper_v1.jsonl | 458 | fail | {"main_idea":"This text reports a study on what affects corporate sustainability. It finds that profitability, audit ... |
| 22 | academic_book | long | academic_book:000034:6a7b7405aca4 | academic_book_v1.jsonl | 34 | pass | {"main_idea":"The text explains how air moves into and out of the lungs and how gases are exchanged. It also shows ho... |
| 19 | academic_book | short | academic_book:000012:79afde415735 | academic_book_v1.jsonl | 12 | pass | {"main_idea":"The text explains linked genes and how they are inherited together during meiosis. It also says that re... |
| 57 | academic_paper | long | academic_paper:000143:ee82b3724a67 | academic_paper_v1.jsonl | 143 | pass | {"main_idea":"The text describes a new species of Glycera from the saltmarsh of Bangladesh. It also gives the study s... |
| 2 | assignment_rubric | long | assignment_rubric:000028:91c8600af9d2 | assignment_rubric_v1.jsonl | 28 | pass | {"main_idea":"The source text gives an assignment for a long academic paper on Islam, patriarchy, and Fatima Mernissi... |
| 1 | assignment_rubric | medium | assignment_rubric:000012:06281f8639e7 | assignment_rubric_v1.jsonl | 12 | pass | {"main_idea":"The text is an assignment brief for writing an abstract about blockchain in supply chain management. It... |
| 139 | gen_know | long | gen_know:000072:94f2a77b2a74 | gen_know_v1.jsonl | 72 | pass | {"main_idea":"This text is a short biography of Robert Fico, a Slovak politician. It says he became Prime Minister se... |
| 136 | gen_know | short | gen_know:000032:08bc0f65b4d8 | gen_know_v1.jsonl | 32 | pass | {"main_idea":"This text explains a Supreme Court of Canada decision about Manitoba’s VLT plebiscite law. The court sa... |
| 110 | medlineplus | long | medlineplus:000005:2fe7f0c5f043 | medlineplus_v1.jsonl | 5 | pass | {"main_idea":"The text explains what cholesterol is and how LDL and HDL affect health. It also gives ways to check, l... |
| 114 | medlineplus | short | medlineplus:000034:6129f88ea88a | medlineplus_v1.jsonl | 34 | pass | {"main_idea":"The text explains what germs are and how they spread. It also gives simple ways to help prevent the spr... |
| 108 | public_service | long | public_service:000185:42d911a593cc | public_service_v1.jsonl | 185 | pass | {"main_idea":"This text explains how to apply for a green card and what steps you must take. It also says you must me... |
| 90 | public_service | short | public_service:000006:1a2b4a6cc4a4 | public_service_v1.jsonl | 6 | pass | {"main_idea":"The text explains how to get municipal court records. It says these records are held by each court, and... |
| 16 | tech_doc | long | tech_doc:000059:1ee58ebb3c03 | tech_doc_v1.jsonl | 59 | pass | {"main_idea":"The text explains what game programming is and why it matters. It says game developers should choose th... |
| 9 | tech_doc | short | tech_doc:000008:7b654457efac | tech_doc_v1.jsonl | 8 | pass | {"main_idea":"The text explains how serial data links use ACK-NAK error correction. It says packets are checked with ... |
| 111 | medlineplus | medium | medlineplus:000007:8b87871d5684 | medlineplus_v1.jsonl | 7 | pass | {"main_idea":"The text explains what adenoids are and why enlarged adenoids can be a problem. It also describes how d... |
| 91 | public_service | medium | public_service:000013:7b4fb0bf1e11 | public_service_v1.jsonl | 13 | pass | {"main_idea":"The text explains who needs a Schengen visa to visit Spain as a tourist and how to apply for one. It al... |

## Manual Review

Reviewed 17 final test examples: at least 2 from each of the 7 domains, with short, medium, and long buckets represented. The review included both deterministic failures, `medlineplus`, `public_service`, `assignment_rubric`, long academic examples, and public-service examples with fees, numbers, eligibility rules, and time windows.

Manual labels: `pass` 14, `minor_issue` 2, `major_issue` 1, `uncertain` 0.

| Row | Domain | Bucket | Label | Reason |
| --- | --- | --- | --- | --- |
| 1 | assignment_rubric | medium | pass | Summarizes the blockchain abstract assignment instead of writing the abstract; preserves length, section, keyword, and technical-detail requirements. |
| 2 | assignment_rubric | long | pass | Correctly treats the Islam/patriarchy text as an assignment brief and preserves word-count, style, topic, and required content constraints. |
| 9 | tech_doc | short | pass | Faithful ACK-NAK/CRC serial-link summary with valid JSON and clear resend/acknowledgment logic. |
| 16 | tech_doc | long | pass | Captures game-programming purpose, design risk, language-learning advice, sound, and input concerns without following any embedded command. |
| 19 | academic_book | short | pass | Faithfully summarizes linked genes, recombination distance, linkage maps, and the Mendel note. |
| 22 | academic_book | long | pass | Strong lung mechanics and gas-exchange summary; preserves pressure gradients, resistance, compliance, respiratory control, and partial pressure direction. |
| 57 | academic_paper | long | pass | Accurately covers the new Glycera species, Bangladesh site, morphology, methods, and specimen deposit at a high level. |
| 66 | academic_paper | short | pass | Deterministic sentence heuristic failed because of `E. coli`; the JSON shape is valid and the content is faithful. |
| 87 | academic_paper | medium | major_issue | Content is broadly faithful, but the model produced 7 key points instead of exactly 4, so it fails the required output schema. |
| 90 | public_service | short | pass | Preserves municipal-court record ownership, access routes, business-hours limits, per-page fees, and variable response timing. |
| 91 | public_service | medium | minor_issue | Preserves visa eligibility, 90-day rule, 64 euro fee, legal-resident consulate rule, and payment method, but omits the one-or-two-week processing window. |
| 108 | public_service | long | pass | Preserves green-card visa availability, category eligibility, forms/fees/photos, possible biometrics/support/medical/interview steps, and 10-year renewal. |
| 110 | medlineplus | long | pass | Faithful cholesterol/LDL/HDL summary with risk, testing, lifestyle, medicines, and apheresis options handled safely. |
| 111 | medlineplus | medium | pass | Faithfully explains adenoids, age shrinkage, enlarged-adenoid symptoms, diagnosis, and medical/surgical treatment options. |
| 114 | medlineplus | short | pass | Preserves germ types, transmission paths, and prevention steps including handwashing, staying home, cough covering, and cleaning surfaces. |
| 136 | gen_know | short | pass | Correctly summarizes the Manitoba VLT plebiscite case, provincial power, binding vote, and Charter sections without actual mojibake. |
| 139 | gen_know | long | minor_issue | Overall Robert Fico biography is useful and mostly faithful, but it appears to fuse the 1998 party-role detail with Smer leadership/founding timing, which the source places in 1999. |

Manual review found no refusal/meta behavior, no instruction-following failure, no medical or public-service safety warning reversal, and no broad domain or length-bucket collapse. The main concern is the isolated but real output-contract failure on row 87.

## Recommendation

Recommendation: `central_review_required_before_final_selection`.

Candidate A is strong overall on the final held-out test: JSON parsing is 145/145, schema compliance is 144/145, no mojibake/code-fence/refusal/extra-text leakage was detected, and manual review found no severe faithfulness, safety, or instruction-following issue. However, the single schema failure generated 7 key points instead of the required 4, and manual review found two additional minor precision/omission issues. This is not a `do_not_select_without_fix` result, but central-brain review should decide whether the one held-out format miss is acceptable before declaring Candidate A the final selected artifact.
