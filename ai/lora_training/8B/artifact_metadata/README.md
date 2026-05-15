# ClearRead Llama 3.1 8B QLoRA Candidate A

Last updated: 2026-04-28

This directory is a local metadata pointer for the selected final raw adapter. It does not duplicate model weights.

- Artifact name: `clearread_llama31_8b_qlora_candidate_a`
- Selection status: selected final raw adapter for this training cycle
- Adapter directory: `ai/lora_training/models/adapters/full_candidate_a_3epoch`
- Base model: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Training config: `configs/train_llama31_8b_qlora_candidate_a.example.yaml`
- Inference config: `configs/final_candidate_a_inference.example.yaml`
- Final test report: `reports/FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md`

The adapter itself remains in `models/adapters/full_candidate_a_3epoch`. The full adapter weights, base model weights, checkpoints, optimizer states, and cache files are large runtime artifacts and are not included in this package.

Use `docs/local_inference_runbook.md` for local inference commands and schema guard behavior.
