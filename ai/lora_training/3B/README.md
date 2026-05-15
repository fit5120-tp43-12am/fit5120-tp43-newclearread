# ClearRead 3B-Scale Replacement Experiment Package

This folder contains the cleaned evidence package for the 3B-scale model replacement experiment.

The experiment asked whether a smaller 3B-4B model could replace the previous `Llama 3.1 8B Candidate A` model for the ClearRead structured summarisation task.

## Final Recommendation

The final practical recommendation from this experiment is:

```text
Llama 3.2 3B Instruct + SFT + QLoRA
Base model: unsloth/Llama-3.2-3B-Instruct-bnb-4bit
Selected checkpoint: phase2_r32_a64_lr1p5e4_epoch_4
LoRA rank / alpha: r=32, alpha=64
Learning rate: 1.5e-4
```

The previous 8B baseline remains stronger on strict parser stability, but the selected 3B checkpoint is the best practical replacement found in this experiment. It scored close to the 8B baseline on content quality, had no severe failures, avoided invalid JSON, and used less GPU memory in the local benchmark route.

## Where To Start

Read these files in order:

1. `reports/final/school_final_3b_experiment_report_en.md` - full school-facing final report.
2. `reports/phase2/compressed_candidate_ranking.json` - Phase2 validation ranking used before frozen benchmark.
3. `benchmark/llama32_phase2_frozen/system_score_summary.json` - final Llama 3.2 3B frozen benchmark score summary.
4. `benchmark/phi4_phase2_frozen/system_score_summary.json` - final Phi-4-mini frozen benchmark score summary.
5. `reports/data_audit/training_pair_random_audit_100_20260513.md` - 100-pair training-data audit.
6. `reports/deployment_feasibility/local_inference_resource_probe_20260513.md` - local inference memory and latency probe.
7. `reports/optimization/OPTIMIZATION_REPORT_EN.md` - earlier Llama 3.2 3B-only optimisation pass.

## Package Structure

```text
3B/
  benchmark/                 Compact frozen benchmark evidence
  configs/                   Model, evaluation, and judge configuration files
  logs/decisions/            Sanitised decision notes and progress records
  manifests/                 Snapshot and evidence manifests
  reports/                   Final report and supporting experiment reports
  scripts/                   Training, validation, benchmark, audit, and monitoring scripts
```

## Large Artifact Policy

Large runtime artifacts are represented through reports, manifests, hashes, and compact score files. This keeps the package focused on review and traceability while model weights, base-model cache files, raw datasets, optimiser checkpoints, full generated output directories, and raw API response dumps remain outside the Git package.

## Package Manifest

`manifests/package_manifest.json` records the relative path, size, and SHA256 hash of each file included in this 3B evidence package.

## Relationship To The 8B Package

The `../8B/` folder contains the original Llama 3.1 8B Candidate A training package. The final 3B report compares against that model as the fixed baseline.
