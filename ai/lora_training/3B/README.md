# Clearead 3B Model Selection Package

This folder contains the 3B-scale model comparison and final selection evidence for the Clearead structured summarisation task.

## Selected Checkpoint

```text
Base model: unsloth/Llama-3.2-3B-Instruct-bnb-4bit
Training method: SFT + QLoRA
Selected checkpoint: phase2_r32_a64_lr1p5e4_epoch_4
LoRA rank / alpha: r=32, alpha=64
Learning rate: 1.5e-4
Global step: 584
```

The selected checkpoint is the practical deployment recommendation for the 3B route. It combines strong content quality, valid structured output behaviour, no severe benchmark failures, and lower memory demand than the 8B baseline.

## Review Path

Read these files in order:

1. [reports/final/school_final_3b_experiment_report_en.md](reports/final/school_final_3b_experiment_report_en.md): full school-facing final report.
2. [reports/school_facing/index/README.md](reports/school_facing/index/README.md): index of testing, deployment, and safety/privacy reports.
3. `reports/school_facing/index/EVIDENCE_TO_REPORT_MATRIX.md`: evidence-to-report allocation matrix.
4. [reports/phase2/compressed_candidate_ranking.json](reports/phase2/compressed_candidate_ranking.json): Phase 2 validation ranking before frozen benchmark.
5. [benchmark/llama32_phase2_frozen/system_score_summary.json](benchmark/llama32_phase2_frozen/system_score_summary.json): final Llama 3.2 3B frozen benchmark summary.
6. [benchmark/phi4_phase2_frozen/system_score_summary.json](benchmark/phi4_phase2_frozen/system_score_summary.json): final Phi-4-mini frozen benchmark summary.
7. [reports/data_audit/training_pair_random_audit_100_20260513.md](reports/data_audit/training_pair_random_audit_100_20260513.md): random audit of 100 training pairs.
8. [reports/deployment_feasibility/local_inference_resource_probe_20260513.md](reports/deployment_feasibility/local_inference_resource_probe_20260513.md): local memory and latency feasibility probe.
9. [reports/optimization/OPTIMIZATION_REPORT_EN.md](reports/optimization/OPTIMIZATION_REPORT_EN.md): Llama 3.2 3B optimisation pass.

## Package Structure

```text
3B/
  benchmark/      Compact frozen benchmark evidence
  configs/        Model, evaluation, and judge configuration files
  logs/           Sanitised decision notes and progress records
  manifests/      Package, benchmark, and evidence manifests
  reports/        Final report and supporting experiment reports
  scripts/        Training, validation, benchmark, audit, and monitoring scripts
```

## Relationship To Other Packages

- [../8B/](../8B/README.md) contains the Llama 3.1 8B Candidate A baseline package used for comparison.
- [../../model_deployment/3B/](../../model_deployment/3B/README.md) contains the FastAPI and vLLM deployment package for the selected 3B checkpoint.

## Artifact Policy

Large runtime artifacts are represented through reports, manifests, hashes, and compact score files. Model weights, base-model caches, raw datasets, optimizer checkpoints, full generated output directories, and raw API response dumps remain outside the Git package.

`manifests/package_manifest.json` records the relative path, size, and SHA256 hash of each included evidence file.
