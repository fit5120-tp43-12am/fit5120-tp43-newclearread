# Final Data QA Summary

## Final Counts

| Category | Count |
| --- | ---: |
| source records | 1537 |
| accepted training records | 1452 |
| quarantined audit records | 85 |
| accepted + quarantine coverage | 1537 |

## Per-Dataset Accepted Counts

| Dataset | Accepted |
| --- | ---: |
| assignment_rubric | 83 |
| tech_doc | 89 |
| academic_book | 233 |
| academic_paper | 486 |
| public_service | 198 |
| medlineplus | 230 |
| gen_know | 133 |

## Structural QA

The final accepted set passed structural validation:

- every accepted line parses as JSON,
- every accepted record uses `messages`,
- every accepted record has `system | user | assistant` role order,
- every `assistant.content` parses as JSON,
- assistant JSON contains exactly `main_idea` and `key_points`,
- `main_idea` has exactly 2 sentence-like units,
- `key_points` contains exactly 4 items,
- every key point is one sentence-like unit,
- accepted/quarantine overlap is 0,
- missing source records is 0.

## Recovery QA

The first full regeneration produced 1375 accepted records and 162 quarantines. A hotspot review identified recoverable technical issues in public-service sentence splitting and judge response truncation. A targeted recovery rerun processed 100 allowlisted records and recovered 77 of them.

Final remaining quarantines were kept out of training.

## Known Limitations

- MedlinePlus remains the hardest domain because dense medical pages can lose important diagnosis, treatment, prevention, risk, or warning details under a strict `2 + 4` output target.
- The final accepted dataset has strong structural validation and targeted semantic review, but not a full human semantic review of every accepted record.
- The 85 quarantined records reduce coverage slightly, but keep the v1 training set cleaner.
