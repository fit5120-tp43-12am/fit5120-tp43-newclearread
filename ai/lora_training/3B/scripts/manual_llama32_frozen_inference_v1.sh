#!/usr/bin/env bash
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root" || exit 2

stamp="20260514_llama32_frozen_v1"
log_dir="logs/command_outputs"
test_dir="logs/tests"
mkdir -p "$log_dir" "$test_dir"

log_path="$log_dir/manual_final_inference_llama32_3b_${stamp}.log"
exit_path="$test_dir/manual_final_inference_llama32_3b_${stamp}.exitcode"

cmd=(
  python scripts/run_finalist_benchmark_inference.py
  --candidate-key llama32_3b_instruct
  --system-id compressed_final_llama32_3b_instruct_phase2_r32_a64_lr1p5e4_epoch_4
  --benchmark-run-id phase2_llama32_frozen_benchmark_20260514_v1
  --adapter-dir "$root/model_workspaces/llama32_3b_instruct/models/adapters/phase2_r32_a64_lr1p5e4_epoch_4"
  --max-new-tokens 320
)

{
  printf '{"event":"command_started","created_at_utc":"%s","cmd":' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '%s\n' "${cmd[@]}" | python -c 'import json,sys; print(json.dumps([line.rstrip("\n") for line in sys.stdin]))'
  printf '}\n'
  "${cmd[@]}"
} > "$log_path" 2>&1

code=$?
printf '%s\n' "$code" > "$exit_path"
exit "$code"
