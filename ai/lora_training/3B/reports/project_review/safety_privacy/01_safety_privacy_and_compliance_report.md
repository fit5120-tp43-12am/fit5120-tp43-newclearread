# Safety, Privacy, And Compliance Report

## Project Purpose

This report explains the safety, privacy, and traceability controls used during the 3B-scale ClearRead model replacement experiment. The experiment reused earlier project data and benchmark evidence, so the workflow needed careful separation between old artifacts, new training runs, judge calls, and Git-ready review material.

## Work Completed

The following controls were used:

| Area | Control |
|---|---|
| Workspace isolation | New 3B work was placed under isolated experiment folders and later cleaned into `ai/lora_training/3B`. |
| Old artifact handling | Earlier 8B and benchmark evidence were reused as fixed baseline evidence. |
| Evidence integrity | Manifests, hashes, score summaries, parse-failure files, and decision notes were preserved. |
| Git package policy | The Git package stores compact review artifacts; large weights, caches, raw generated directories, and raw API dumps remain in the local experiment workspace. |
| Credential handling | API credentials were passed through the runtime environment and omitted from reports. |
| Safety scoring | Judge scoring included source-safety margin, safety caps, severe-failure counts, and major-risk counts. |
| Output reliability | Parser checks recorded invalid JSON, sentence-count issues, key-point-count issues, markdown fences, refusal/meta behaviour, and mojibake risk. |

## Rationale

The experiment needed project review evidence that was complete enough for review and clean enough for repository sharing. The package therefore stores scripts, reports, summaries, manifests, and compact benchmark outputs. Full local runtime artifacts remain in the experiment workspace for traceability.

The safety scoring design also matched the ClearRead task. The product summarises source text for reading support, so source faithfulness and safe simplification are essential. The judge rubric separated content safety from formatting readiness.

## Verification Results

Key integrity and compliance results:

| Check | Result |
|---|---|
| Final 3B package location | `ai/lora_training/3B` |
| Package manifest | `manifests/package_manifest.json` |
| Evidence inventory | `reports/evidence/evidence_inventory.md` |
| Deletion operations recorded for packaging | 0 |
| Old 8B baseline score reused as fixed evidence | 78.055556 |
| Final Llama 3B severe failures | 0 |
| Final Llama 3B invalid JSON failures | 0 |
| Final Phi-4-mini severe failures | 1 |
| Final Phi-4-mini invalid JSON failures | 1 |

Safety-level benchmark evidence:

| System | Clear pass | Minor risk | Moderate risk | Major risk | Severe fail |
|---|---:|---:|---:|---:|---:|
| Llama 3.2 3B Phase2 | 12 | 60 | 49 | 11 | 0 |
| Phi-4-mini Phase2 | 10 | 47 | 54 | 8 | 1 |

Data-quality safety evidence:

| Audit result | Count |
|---|---:|
| Accept as-is | 90 |
| Minor repair | 10 |
| Rewrite | 0 |
| Drop or manual review | 0 |

The audit tagged minor health-warning and requirement-detail issues, which gives future work a targeted repair list.

## Deployment Observations And Handling

The deployment path highlighted two practical safety and reliability points.

First, invalid JSON creates a product-level reliability risk because the frontend needs a parseable object. Llama 3.2 3B had 0 invalid JSON failures in the final frozen benchmark. Phi-4-mini had 1 invalid JSON failure, which weakened confidence in its deployment readiness.

Second, variable key-point count has lower product impact because the frontend can accept a dynamic number of key points. The final reporting keeps strict parser results visible while also explaining the product impact of each failure type.

Credential handling was also checked during manual Llama scoring. The API key was supplied through the WSL environment for runtime use, and the reports record paths, commands, and outcomes while keeping the key out of report content.

## Final Conclusion

The 3B experiment package is suitable for project review. It keeps evidence traceable, separates compact review artifacts from large runtime files, preserves safety-scoring outputs, and records deployment-relevant reliability risks.

The safety and privacy evidence supports the final choice of Llama 3.2 3B because it achieved 0 severe benchmark failures, 0 invalid JSON failures, a smaller local GPU footprint, and a clear evidence trail.

## Evidence Locations

| Evidence | Path |
|---|---|
| Package manifest | `manifests/package_manifest.json` |
| Evidence inventory | `reports/evidence/evidence_inventory.md` |
| Judge prompt/schema | `configs/judge_prompt_schema_candidate_v1_1.md` |
| Llama benchmark summary | `benchmark/llama32_phase2_frozen/system_score_summary.json` |
| Phi benchmark summary | `benchmark/phi4_phase2_frozen/system_score_summary.json` |
| Training data audit | `reports/data_audit/training_pair_random_audit_100_20260513.md` |
| Final technical report | `reports/final/final_3b_experiment_report_en.md` |
| Evidence allocation matrix | `reports/project_review/index/EVIDENCE_TO_REPORT_MATRIX.md` |
