# Manual Llama 3.2 Frozen Benchmark - 2026-05-14

## Purpose

Run the frozen benchmark for the strongest Llama 3.2 3B Phase2 checkpoint after the compressed Phase2 finalist workflow completed the Phi finalist benchmark first.

## Candidate

- Candidate key: `llama32_3b_instruct`
- Base model: `unsloth/Llama-3.2-3B-Instruct-bnb-4bit`
- Adapter: `model_workspaces/llama32_3b_instruct/models/adapters/phase2_r32_a64_lr1p5e4_epoch_4`
- Training config: `r=32`, `alpha=64`, `lr=1.5e-4`, epoch `4`
- Frozen benchmark run id: `phase2_llama32_frozen_benchmark_20260514_v1`
- Judge run id: `phase2_llama32_frozen_benchmark_judge_20260514_v1`
- System id: `compressed_final_llama32_3b_instruct_phase2_r32_a64_lr1p5e4_epoch_4`

## Execution Notes

- Inference was run through `scripts/manual_llama32_frozen_inference_v1.sh`.
- The first manual background launch failed before model inference due to command wrapping, then the foreground WSL run completed.
- Windows had `OPENAI_API_KEY`; WSL required explicit environment forwarding. The judge run was completed after passing the key into WSL via `WSLENV=OPENAI_API_KEY/u`.
- Old benchmark artifacts stayed unchanged.

## Results

- Prepared inputs: `145`
- Raw outputs: `145`
- Parsed outputs: `134/145`
- Parse failures: `11/145`
- Parse failure reasons:
  - `key_point_not_one_sentence`: `6`
  - `key_points_not_four_string_items`: `2`
  - `main_idea_not_two_sentences`: `3`
- Inference runtime: `1250.54` seconds
- Peak allocated VRAM: `2831.85` MiB
- Judge inputs: `134`
- Schema-valid judge outputs: `132`
- Judge validation failures: `4`
- Mean capped official item score: `75.848485`
- Severe fails: `0`
- Major risks: `11`
- Source safety margin mean: `3.189394`
- Main message salience mean: `4.022727`

## Comparison Snapshot

- Old Llama 3.1 8B Candidate A: score `78.055556`, parsed `144/145`
- Phi-4-mini Phase2 frozen benchmark: score `75.041667`, parsed `136/145`, schema-valid judge outputs `120`
- Llama 3.2 3B Phase2 frozen benchmark: score `75.848485`, parsed `134/145`, schema-valid judge outputs `132`

## Interpretation

Llama 3.2 3B scored slightly higher than the already completed Phi frozen benchmark on schema-valid judged rows, but it had lower parse/product readiness than both Phi and the old 8B baseline. It remains below the old 8B Candidate A by about `2.21` points and has `10` more parse failures than the old 8B baseline.
