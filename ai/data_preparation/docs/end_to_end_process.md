# End-to-End Data Preparation Process

This document explains the data preparation path from source collection to the final accepted LoRA training dataset.

## 1. Source Collection

Seven source groups were prepared to cover the reading-support summarization use case:

| Group | Source | Purpose |
| --- | --- | --- |
| MedlinePlus | MedlinePlus health-topic XML export | medical and public-health explanations |
| assignment_rubric | RubricHub writing subset | assignment and rubric-style requirements |
| tech_doc | Wikimedia technical/tutorial pages | technical documentation and tool instructions |
| academic_book | OpenStax textbook text | academic textbook explanations |
| academic_paper | open-access academic paper excerpts | research-paper style dense prose |
| public_service | WikiHow-style public-service guides | administrative and process explanations |
| gen_know | Wikipedia article excerpts | general knowledge and background explanations |

Each extracted example was required to be single-source: one record came from one topic, article, chapter window, paper excerpt, or guide page.

## 2. Early Per-Source Processing

Each source group first had its own scripts for:

1. source probing,
2. extraction and filtering,
3. word-count bucketing,
4. raw target generation,
5. SFT JSONL export,
6. validation,
7. manual or script-assisted repair.

The early SFT files already used `messages` records, but their label style was inconsistent. Some used two or three `main_idea` sentences, and `key_points` ranged from short fixed lists to long variable lists.

## 3. Repair And Cleanup Before The Final Rebuild

Several source groups required cleanup before the final rebuild:

- `assignment_rubric` was reduced from an initial 150-row target to 89 higher-quality rows.
- `tech_doc` had one broken SFT row removed and was locked at 99 records.
- `gen_know` had one broken SFT row removed and was locked at 149 records.
- `public_service` had off-domain and mismatched records replaced from a stricter candidate pool.
- `academic_book` had duplicate windows, broken starts, and noisy textbook fragments repaired.
- `academic_paper` had broken starts and tails trimmed or replaced.
- `medlineplus` had many rows restored or regenerated from the frozen XML-derived source.

These repairs produced seven cleaned/repaired source SFT files with 1537 valid source records.

## 4. Target Format Redesign

The final v1 target was redesigned for LoRA consistency.

The approved target:

- keeps the chat-style SFT `messages` structure,
- treats the `user` message as source text to summarize,
- writes `assistant.content` as a JSON string,
- fixes `main_idea` to exactly 2 short faithful sentences,
- fixes `key_points` to exactly 4 short high-level sentences,
- preserves warnings, restrictions, requirements, modality, negation, and major conclusions when important.

This fixed `2 + 4` shape was chosen to reduce label entropy while still allowing enough coverage for dense source texts.

## 5. Final LoRA Regeneration Pipeline

The final pipeline is implemented under `final_lora_pipeline/`.

It performs:

1. source validation against locked expected counts,
2. source text extraction from the original `user` message,
3. OpenAI generation of candidate labels,
4. structural validation of the assistant JSON,
5. semantic judging against the source text,
6. retry on structural or semantic failure,
7. accepted output writing,
8. quarantine output writing,
9. checkpointing, logging, and reporting.

The pipeline includes drift protection. It refuses to continue from an existing checkpoint if the prompt, config, model, or source manifest changes unless an explicit override is used.

## 6. Pilot Run

A 14-record pilot was run first: two records per source group.

Pilot result:

- processed: 14
- accepted: 14
- quarantined: 0
- structural failures: 0

The pilot confirmed that the implementation could run end to end before the full regeneration.

## 7. Full Regeneration

The first full regeneration covered 1537 source records.

Stage 6 result:

| Dataset | Accepted | Quarantined |
| --- | ---: | ---: |
| assignment_rubric | 83 | 6 |
| tech_doc | 89 | 10 |
| academic_book | 231 | 19 |
| academic_paper | 484 | 16 |
| public_service | 154 | 46 |
| medlineplus | 201 | 49 |
| gen_know | 133 | 16 |
| Total | 1375 | 162 |

The full run completed technically, but it was not accepted as final because public-service, MedlinePlus, and judge-invalid outputs needed review.

## 8. Hotspot Review And Targeted Recovery

The hotspot review found three separate issues:

1. Many public-service structural failures were false positives caused by sentence splitting around dotted abbreviations and web-domain patterns.
2. Judge invalid-output failures were mostly response truncation from too-low judge output token limits.
3. MedlinePlus failures were often true semantic difficulty because medical pages are dense and safety-critical.

The project used a targeted recovery strategy instead of a full redesign.

The recovery patch:

- improved sentence splitting for abbreviations and domain patterns,
- raised judge output token budget,
- detected incomplete judge responses explicitly,
- reran only an allowlisted recovery set,
- wrote recovery results into a separate namespace.

Recovery result:

- allowlisted records processed: 100
- accepted: 77
- remained quarantined: 23

## 9. Final Merge And QA

The final merge:

1. kept Stage 6 accepted records,
2. added accepted recovery records,
3. removed recovered records from the Stage 6 quarantine set,
4. kept remaining quarantine records as audit exclusions.

Final result:

- accepted: 1452
- quarantined: 85
- total covered: 1537
- missing source records: 0
- accepted/quarantine overlap: 0
- accepted structural validation issues: 0

## 10. Training-System-Clean Copy

A final derived copy was created for training.

That copy replaces only the system prompt in accepted training records while verifying that:

- the user source text is unchanged,
- the assistant label is unchanged,
- quarantine files remain byte-identical audit artifacts.

This produces the final recommended training namespace while preserving the earlier final merge namespace for audit comparison.
