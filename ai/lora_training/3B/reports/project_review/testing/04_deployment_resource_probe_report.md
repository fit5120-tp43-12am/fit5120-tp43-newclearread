# Deployment Resource Probe Report

## Project Purpose

The deployment probe measured whether the smaller model candidates offered a practical resource advantage over the earlier Llama 3.1 8B Candidate A model. The project goal required output quality and deployability, so GPU memory and inference speed were measured alongside benchmark quality.

## Work Completed

The old 8B model and the 3B-4B candidates were run on the same local machine with the same script, sample selection, prompt style, loading policy where applicable, and sequential generation route.

Test setup:

| Item | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 4070 Ti SUPER |
| Reported GPU memory | 16376 MiB |
| Environment | WSL conda `clearread-llama-lora` |
| Route | Local single-process sequential inference |
| Max input tokens | 3072 |
| Max new tokens | 256 |
| Sample seed | 20021 |

## Rationale

A smaller parameter count can still produce slower end-to-end inference when a model generates more tokens, loads through a different runtime path, or uses a heavier architecture. A local resource probe aligned the comparison background before deployment decisions were made.

## Verification Results

| Model | Load s | Peak GPU MiB | 1 block s | 3 blocks total s | Mean s/block | Parse 3/3 | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Llama 3.1 8B Candidate A | 154.969 | 7889 | 4.693 | 13.434 | 4.478 | 3/3 | completed |
| Llama 3.2 3B Instruct | 61.857 | 3688 | 6.640 | 15.852 | 5.284 | 0/3 | completed |
| Ministral 3B | 177.364 | 4135 | 5.907 | 18.815 | 6.272 | 1/3 | completed |
| Granite 4.1 3B | 126.135 | 3739 | 8.535 | 25.283 | 8.428 | 1/3 | completed |
| Phi-4-mini | 146.952 | 4547 | 7.737 | 20.971 | 6.990 | 2/3 | completed |
| Qwen 3.5 4B | 182.323 | 5065 | 8.854 | 28.255 | 9.418 | 0/3 | completed |
| Gemma 4 E2B IT | 193.821 | 8199 | 17.463 | 32.649 | 10.883 | 2/3 | completed |
| Gemma 4 E4B IT | 310.970 | 10951 | 20.559 | 46.776 | 15.592 | 3/3 | completed |

The selected Llama 3.2 3B candidate used much less local GPU memory than the old 8B model in this route: 3688 MiB versus 7889 MiB.

## Deployment Observations And Handling

The old 8B model was fast in this small sequential test because it generated shorter, schema-compliant outputs after fine-tuning. The Llama 3.2 3B base route used less memory and loaded faster, then required fine-tuning and benchmark checks to judge product quality.

Gemma E4B had promising prompt-only formatting behaviour, yet its local memory and latency were poorly aligned with the replacement goal. It moved to evidence-only status after the feasibility check.

The final model choice treated deployment as a combined decision: strict benchmark score, content quality, invalid JSON risk, severe failure count, GPU memory, and engineering maintainability.

## Final Conclusion

The deployment probe supported Llama 3.2 3B as the most practical small-model replacement candidate from the completed search. It delivered a large memory reduction compared with the 8B baseline and avoided the high local cost observed for Gemma E4B.

## Evidence Locations

| Evidence | Path |
|---|---|
| Local resource probe | `reports/deployment_feasibility/local_inference_resource_probe_20260513.md` |
| Gemma versus 8B feasibility report | `reports/deployment_feasibility/gemma_e4_vs_llama8b_deployment_feasibility_20260513.md` |
| Final recommendation report | `reports/final/final_3b_experiment_report_en.md` |
| Evidence allocation matrix | `reports/project_review/index/EVIDENCE_TO_REPORT_MATRIX.md` |
