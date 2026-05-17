# Frozen Benchmark And Content Quality Report

## Project Purpose

The final benchmark tested whether the best 3B-scale candidates could approach the earlier Llama 3.1 8B Candidate A model on the same frozen ClearRead benchmark. The benchmark used preserved prepared inputs from the earlier test workflow.

## Work Completed

The final comparison used the old 8B benchmark score as the fixed baseline and ran final benchmark evidence for the new 3B-scale candidates.

Systems compared:

| System | Role |
|---|---|
| Llama 3.1 8B Candidate A | Previous fixed baseline |
| Llama 3.2 3B Phase2 | Final practical 3B replacement candidate |
| Phi-4-mini Phase2 | Strong validation finalist |

The benchmark recorded raw outputs, parser results, judge inputs, judge outputs, score summaries, parse failures, and system-level aggregate results.

## Rationale

Validation scores were useful for selecting candidates, while final model choice required a frozen benchmark. The frozen benchmark protected the decision from repeated tuning on the same validation subset.

The benchmark also separated strict parser readiness from product interpretation. The product frontend can accept a dynamic number of key points, so key-point-count variation has lower product impact than invalid JSON or severe content risk.

## Verification Results

### Strict Benchmark Results

| System | Score | Parsed | Judge-valid outputs | Before-cap score | Severe | Major |
|---|---:|---:|---:|---:|---:|---:|
| Old Llama 3.1 8B Candidate A | 78.055556 | 144/145 | 144 | 85.965278 | 0 | 5 |
| Llama 3.2 3B Phase2 | 75.848485 | 134/145 | 132 | 82.780303 | 0 | 11 |
| Phi-4-mini Phase2 | 75.041667 | 136/145 | 120 | 83.558333 | 1 | 8 |

### Parse Failure Types

| System | Parse failures | Main failure types |
|---|---:|---|
| Llama 3.2 3B Phase2 | 11 | key-point sentence issues, key-point count issues, main-idea sentence-count issues |
| Phi-4-mini Phase2 | 9 | key-point sentence issues, main-idea sentence-count issues, invalid JSON |

### Content Difference Against 8B

For Llama 3.2 3B against the old 8B model, the comparison used 131 shared valid input IDs:

| Metric | Average difference, Llama minus 8B |
|---|---:|
| Main message salience | -0.1679 / 5 |
| Source safety margin | -0.1832 / 5 |
| Plain language | -0.1908 / 5 |
| Cognitive-load reduction | -0.1603 / 5 |
| Sentence accessibility | -0.1832 / 5 |
| Scannability | -0.0992 / 5 |

For Phi-4-mini against the old 8B model, the comparison used 119 shared valid input IDs:

| Metric | Average difference, Phi minus 8B |
|---|---:|
| Main message salience | -0.0924 / 5 |
| Source safety margin | -0.2017 / 5 |
| Plain language | -0.1597 / 5 |
| Cognitive-load reduction | -0.2185 / 5 |
| Sentence accessibility | -0.0840 / 5 |
| Scannability | -0.1176 / 5 |

The strict benchmark favoured the old 8B model. The practical 3B decision favoured Llama 3.2 3B among the new candidates because it scored above Phi in the final frozen benchmark and avoided invalid JSON and severe benchmark failure.

## Deployment Observations And Handling

Llama 3.2 3B produced strict parser failures mainly through sentence-count and key-point-count issues. The current frontend can accept dynamic key point counts, so those cases remain easier to handle than invalid JSON.

Phi-4-mini had strong validation quality, then showed final benchmark reliability concerns through one invalid JSON failure, one severe fail, and a lower judge-valid output count.

The final recommendation reports both strict benchmark results and product-aware interpretation so that formal evaluation and real product behaviour remain visible.

## Final Conclusion

The old 8B model remained strongest on strict benchmark score. The selected Llama 3.2 3B model became the best practical small-model replacement found in the completed search because its content gap was modest, its severe failure count was 0, its invalid JSON failure count was 0, and its deployment footprint was smaller.

## Evidence Locations

| Evidence | Path |
|---|---|
| Llama frozen benchmark summary | `benchmark/llama32_phase2_frozen/system_score_summary.json` |
| Llama parse failures | `benchmark/llama32_phase2_frozen/parse_failures.jsonl` |
| Phi frozen benchmark summary | `benchmark/phi4_phase2_frozen/system_score_summary.json` |
| Phi parse failures | `benchmark/phi4_phase2_frozen/parse_failures.jsonl` |
| Final selection report | `reports/final/compressed_phase2_final_selection_report.json` |
| Main final report | `reports/final/school_final_3b_experiment_report_en.md` |
| Evidence allocation matrix | `reports/school_facing/index/EVIDENCE_TO_REPORT_MATRIX.md` |
