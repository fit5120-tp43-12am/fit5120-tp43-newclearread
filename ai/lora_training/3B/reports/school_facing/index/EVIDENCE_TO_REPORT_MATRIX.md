# Evidence Register And Report Allocation Matrix

## Purpose

This document organises the evidence retained for the ClearRead 3B-scale replacement experiment and assigns each evidence group to the school-facing report set. It is designed as the traceability layer between the final narrative reports and the underlying experiment records.

The main project question was whether a smaller 3B-scale model could replace the earlier `Llama 3.1 8B Candidate A` model for the ClearRead structured summarisation task while keeping useful summary quality and reducing local deployment cost.

## Report Destinations

Paths in the evidence table use the `3B/` folder as root. Windows paths identify raw local evidence locations.

| Code | School-facing destination | Role |
|---|---|---|
| R1 | `reports/school_facing/testing/01_training_data_quality_audit_report.md` | Training-pair quality, label reliability, and dataset suitability. |
| R2 | `reports/school_facing/testing/02_model_training_validation_search_report.md` | Model search history, training settings, validation curves, checkpoint selection, and parameter decisions. |
| R3 | `reports/school_facing/testing/03_frozen_benchmark_and_content_quality_report.md` | Final frozen benchmark results, content quality comparison, parse patterns, and practical quality conclusion. |
| R4 | `reports/school_facing/testing/04_deployment_resource_probe_report.md` | Local inference memory, latency, model loading behaviour, and deployment fit. |
| R5 | `reports/school_facing/safety_privacy/01_safety_privacy_and_compliance_report.md` | Data handling, workspace isolation, API credential handling, manifest coverage, and safety scoring evidence. |
| R6 | `reports/final/school_final_3b_experiment_report_en.md` | Integrated school-facing final report and final model recommendation. |

## Evidence Register

| Evidence group | Main evidence locations | What it proves | Report destination | Placement |
|---|---|---|---|---|
| Previous 8B baseline | `../8B/reports/FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md`; `reports/baseline_reference/old_benchmark_baseline_reference.json`; `benchmark/llama32_phase2_frozen/system_score_summary.json` | The old `Llama 3.1 8B Candidate A` benchmark score, parsed count, and comparison baseline. | R3, R6 | Main comparison table and baseline appendix. |
| Previous 8B training package | `../8B/reports/CLEARREAD_LORA_TRAINING_TECHNICAL_REPORT.md`; `../8B/docs/end_to_end_training_process.md`; `../8B/docs/experiment_history.md` | The first-generation fine-tuning process that created the 8B reference system. | R2, R6 | Background paragraph and traceability appendix. |
| Frozen benchmark design | `configs/judge_prompt_schema_candidate_v1_1.md`; `configs/eval_settings.json`; `manifests/benchmark_snapshot_manifest.json` | The benchmark rubric, scoring schema, judge prompt, and fixed evaluation settings. | R3, R5, R6 | Method section and evidence appendix. |
| Benchmark prepared inputs | `manifests/benchmark_snapshot_manifest.json`; raw source retained in `<local-iteration1-benchmark-workspace>\dyslexia_benchmark_handoff\03_project_workspace\09_run_config\worker_20_dataset_manifest_and_freeze_inputs` | The benchmark input set was frozen and traceable to the earlier benchmark workflow. | R3, R5 | Benchmark setup section and manifest evidence. |
| Training split snapshot | `reports/evidence/evidence_inventory.md`; `manifests/phase2_evidence_inventory.json`; raw source retained in `<local-phase2-search-workspace>\data\source_snapshot\training3b_splits` | The train, validation, and test split files used in the 3B search were copied as a fixed source snapshot. | R1, R2, R5 | Dataset method section and manifest appendix. |
| Training-pair random audit | `reports/data_audit/training_pair_random_audit_100_20260513.md`; `scripts/audit_training_pairs_gpt55.py`; `scripts/sample_training_pairs.py` | A 100-item random sample was reviewed for faithfulness, coverage, abstraction quality, clarity, schema fit, and training value. | R1, R6 | Main report body and audit appendix. |
| Initial 3B Candidate B training | `<local-iteration1-3b-training-workspace>\reports\en\training_process_report_candidate_b.md`; `<local-iteration1-3b-training-workspace>\reports\en\benchmark_report_candidate_b.md`; `reports/optimization/OPTIMIZATION_REPORT_EN.md` | The first Llama 3.2 3B attempt and early benchmark result before the wider model search. | R2, R3, R6 | Experiment history section. |
| Llama-only optimisation pass | `reports/optimization/OPTIMIZATION_REPORT_EN.md`; `reports/optimization/optimization_summary.json`; `logs/decisions/manual_llama32_frozen_benchmark_20260514.md` | Llama 3.2 3B improved through rank, epoch, and prompt-guard trials, reaching a stronger pre-Phase2 result. | R2, R3, R6 | Training search section and benchmark context. |
| Broad Stage 1 anchor search | `reports/stage1/stage1_anchor_summary.csv`; `reports/stage1/stage1_anchor_summary.json`; `reports/stage1/stage1_interim_summary_20260512_v2.md`; `configs/model_candidates.json` | Multiple 3B-4B model families were tested under a common five-epoch QLoRA anchor curve. | R2, R4, R6 | Model search table and candidate narrowing rationale. |
| Stage 2 model selection | `reports/stage2/stage2_top_models.md`; `reports/stage2/stage2_top_models.json`; `logs/decisions/phase2_search_started_20260513_130728.md` | The search narrowed toward Phi-4-mini, Llama 3.2 3B, and Ministral based on validation, deployment, and training stability evidence. | R2, R6 | Candidate selection section. |
| Gemma deployment feasibility | `reports/deployment_feasibility/gemma_e4_vs_llama8b_deployment_feasibility_20260513.md`; `logs/decisions/pause_sweep_for_gemma_vs_llama8b_deployment_check_20260513.md` | Gemma E4B had higher local cost in the tested route and moved to evidence status. | R4, R6 | Deployment comparison and model-family decision note. |
| Local inference resource probe | `reports/deployment_feasibility/local_inference_resource_probe_20260513.md`; `scripts/local_inference_resource_probe.py`; `scripts/summarize_local_inference_probe.py` | Local loading time, peak GPU memory, per-block latency, and parse sanity were measured for candidate families on the same machine. | R4, R6 | Main deployment table and appendix. |
| Compressed Phase2 strategy | `logs/decisions/compressed_plan_takeover_20260514_011914.md`; `logs/decisions/superseded_by_compressed_plan_20260514_002705.md`; `scripts/switch_to_compressed_phase2.py`; `scripts/run_phase2_compressed_search.py` | The experiment shifted from a broad matrix to a focused finalist search with hard selection rules. | R2, R6 | Process-change section and decision appendix. |
| Phi-4-mini validation runs | `logs/decisions/phi4_mini_instruct_phase2_r32_a64_lr1e4_checkpoint_selection_20260513_171031.md`; `logs/decisions/phi4_mini_instruct_phase2_r32_a64_lr1p5e4_checkpoint_selection_20260513_210833.md`; `logs/decisions/phi4_mini_instruct_phase2_r64_a128_lr1e4_checkpoint_selection_20260514_011859.md`; `reports/phase2/compressed_candidate_ranking.json` | Phi-4-mini led the validation subset and required final benchmark confirmation. | R2, R3, R6 | Validation ranking and finalist discussion. |
| Llama 3.2 3B validation run | `logs/decisions/llama32_3b_instruct_phase2_r32_a64_lr1p5e4_checkpoint_selection_20260514_052636.md`; `reports/phase2/compressed_candidate_ranking.json` | Llama 3.2 3B remained a competitive challenger with stronger practical reliability in final testing. | R2, R3, R6 | Training result table and final recommendation. |
| Ministral validation run | `logs/decisions/ministral3_3b_instruct_phase2_r32_a64_lr1p5e4_checkpoint_selection_20260514_092333.md`; `logs/decisions/compressed_ministral3_3b_instruct_r64_skipped_gap_20260514_092333.md`; `reports/phase2/compressed_candidate_ranking.json` | Ministral completed the compressed challenge and ranked below the stronger finalists. | R2, R6 | Candidate comparison section. |
| Rank-search stop decisions | `logs/decisions/compressed_llama32_3b_instruct_r64_skipped_gap_20260514_054603.md`; `logs/decisions/compressed_ministral3_3b_instruct_r64_skipped_gap_20260514_092333.md` | Extra rank-64 expansion was reserved for cases with sufficient validation competitiveness. | R2, R6 | Method explanation and appendix. |
| Seed sanity check | `logs/decisions/phi4_mini_instruct_phase2_seed5141_phase2_r32_a64_lr1p5e4_epoch3_checkpoint_selection_20260514_141717.md`; raw records retained in `<local-phase2-search-workspace>\reports\phase2` | The strongest validation candidate was sanity-checked with an additional seed route before final selection. | R2, R6 | Validation reliability note. |
| Monitoring and command history | `logs/decisions/phase2_monitor_progress_*.md`; `logs/tests/phase2_current_status.json` in the raw Phase2 workspace; `logs/tests/phase2_command_history.jsonl` in the raw Phase2 workspace | Long-running training, post-processing, and benchmark steps were monitored and recorded with status files and command logs. | R2, R5 | Process-control appendix. |
| Phase2 command outputs | `<local-phase2-search-workspace>\logs\command_outputs`; `reports/evidence/evidence_inventory.md` | Training, validation, judge, benchmark, and post-processing commands produced traceable logs and exit-code files. | R2, R3, R5 | Appendix evidence list. |
| Llama final frozen benchmark | `benchmark/llama32_phase2_frozen/system_score_summary.json`; `benchmark/llama32_phase2_frozen/item_scores_all_systems.jsonl`; `benchmark/llama32_phase2_frozen/parse_failures.jsonl`; `logs/decisions/manual_llama32_frozen_benchmark_20260514.md` | Llama 3.2 3B achieved the best final 3B-scale practical result against the frozen benchmark. | R3, R6 | Main result table and failure taxonomy. |
| Phi final frozen benchmark | `benchmark/phi4_phase2_frozen/system_score_summary.json`; `benchmark/phi4_phase2_frozen/item_scores_all_systems.jsonl`; `benchmark/phi4_phase2_frozen/parse_failures.jsonl` | Phi-4-mini's validation lead was weaker than Llama 3.2 3B on final frozen benchmark reliability. | R3, R6 | Finalist comparison and parse analysis. |
| Parse-failure taxonomy | `benchmark/llama32_phase2_frozen/parse_failures.jsonl`; `benchmark/phi4_phase2_frozen/parse_failures.jsonl`; `reports/final/school_final_3b_experiment_report_en.md` | Some strict failures came from key-point count and structure patterns that the current frontend can handle dynamically. | R3, R6 | Content-quality analysis section. |
| Final model selection | `reports/final/compressed_phase2_final_selection_report.json`; `reports/final/school_final_3b_experiment_report_en.md`; selected adapter retained at `<local-phase2-search-workspace>\model_workspaces\llama32_3b_instruct\models\adapters\phase2_r32_a64_lr1p5e4_epoch_4` | The final recommended 3B-scale replacement is Llama 3.2 3B with the Phase2 epoch-4 adapter. | R2, R3, R4, R6 | Executive summary and final conclusion. |
| Safety scoring and risk counts | `benchmark/llama32_phase2_frozen/system_score_summary.json`; `benchmark/phi4_phase2_frozen/system_score_summary.json`; `configs/judge_prompt_schema_candidate_v1_1.md` | Severe failures, major failures, source-safety score, and capped score were tracked as part of model choice. | R3, R5, R6 | Benchmark safety table. |
| Evidence inventories and hashes | `reports/evidence/evidence_inventory.md`; `reports/evidence/evidence_inventory.json`; `manifests/phase2_evidence_inventory.json`; `manifests/package_manifest.json` | Included files, raw workspace records, and Git package artifacts have traceable hashes and sizes. | R5, R6 | Compliance and traceability appendix. |
| Scripts used for reproduction | `scripts/train_sweep_qlora.py`; `scripts/validate_sweep_adapter.py`; `scripts/run_judge_api.py`; `scripts/run_finalist_benchmark.py`; `scripts/manual_llama32_frozen_benchmark.py`; `scripts/generate_evidence_inventory.py` | The main training, validation, judging, benchmarking, and evidence-generation workflow can be inspected from the package scripts. | R2, R3, R5 | Method appendix. |
| Clean Git evidence package | `README.md`; `manifests/package_manifest.json`; `reports/school_facing/index/README.md`; `reports/school_facing/index/EVIDENCE_TO_REPORT_MATRIX.md` | The uploaded package gives reviewers a compact route through reports, configs, scripts, benchmark summaries, decision logs, and manifests. | R5, R6 | Package overview and appendix. |

## Report Allocation Summary

| Report | Evidence that belongs in the main body | Evidence that belongs in the appendix or locations section |
|---|---|---|
| R1: Training Data Quality Audit | Dataset purpose, 100-pair audit method, sample result counts, mean quality dimensions, common minor issues. | Split snapshot, audit script, sample file reference, evidence inventory, training split manifest. |
| R2: Model Training And Validation Search | Initial Llama 3B attempt, Llama-only optimisation, Stage 1 model-family search, Phase2 compressed search, Phi/Llama/Ministral validation scores, checkpoint selection. | Command outputs, training logs, validation logs, judge subset files, decision notes, scripts. |
| R3: Frozen Benchmark And Content Quality | Old 8B baseline, Llama 3B final benchmark, Phi final benchmark, content-score comparison, parse-failure taxonomy, frontend handling context. | Item-score JSONL files, parse-failure JSONL files, judge schema, benchmark manifest. |
| R4: Deployment Resource Probe | Load time, peak GPU memory, latency, local route observations, Gemma feasibility result, Llama 3B deployment advantage. | Probe script, feasibility reports, raw local output location, decision note. |
| R5: Safety, Privacy, And Compliance | Source snapshot handling, workspace isolation, manifest coverage, credential handling, severe-risk scoring, benchmark safety metrics. | SHA256 manifests, package manifest, evidence inventory, command history, decision notes. |
| R6: Final School Report | Project objective, experiment timeline, major direction changes, final benchmark, final recommendation, limitations, deployment conclusion. | Links to R1-R5, final selection JSON, selected adapter path, evidence register. |

## Review Route

For school review, the recommended reading order is:

1. `reports/final/school_final_3b_experiment_report_en.md`
2. `reports/school_facing/index/README.md`
3. `reports/school_facing/index/EVIDENCE_TO_REPORT_MATRIX.md`
4. `reports/school_facing/testing/01_training_data_quality_audit_report.md`
5. `reports/school_facing/testing/02_model_training_validation_search_report.md`
6. `reports/school_facing/testing/03_frozen_benchmark_and_content_quality_report.md`
7. `reports/school_facing/testing/04_deployment_resource_probe_report.md`
8. `reports/school_facing/safety_privacy/01_safety_privacy_and_compliance_report.md`

This order gives the reader the final conclusion first, then the evidence map, then the detailed testing and compliance reports.
