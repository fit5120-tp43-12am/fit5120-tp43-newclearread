#!/usr/bin/env bash
set -uo pipefail

candidate_key="${1:-}"
run_id="${2:-}"
epochs="${3:-5}"
learning_rate="${4:-0.0002}"
lora_r="${5:-32}"
lora_alpha="${6:-64}"
lora_dropout="${7:-0.05}"
primary_batch="${8:-2}"
primary_grad_accum="${9:-4}"
fallback_batch="${10:-1}"
fallback_grad_accum="${11:-8}"

if [[ -z "$candidate_key" || -z "$run_id" ]]; then
  echo "Usage: $0 <candidate_key> <run_id> [epochs] [learning_rate] [lora_r] [lora_alpha] [lora_dropout] [primary_batch] [primary_grad_accum] [fallback_batch] [fallback_grad_accum]" >&2
  exit 2
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root" || exit 2

stamp="$(date +%Y%m%d_%H%M%S)"
log_dir="logs/command_outputs"
test_dir="logs/tests"
mkdir -p "$log_dir" "$test_dir"

record_exit() {
  local name="$1"
  local code="$2"
  printf '%s\n' "$code" > "$test_dir/${name}_${stamp}.exitcode"
}

run_train() {
  local label="$1"
  local batch="$2"
  local grad_accum="$3"
  local log_name="train_${candidate_key}_${run_id}_${label}_${stamp}"
  echo "[train-fallback] ${label}: candidate=${candidate_key} run=${run_id} batch=${batch} grad_accum=${grad_accum}"
  python scripts/train_sweep_qlora.py \
    --candidate-key "$candidate_key" \
    --run-id "$run_id" \
    --epochs "$epochs" \
    --learning-rate "$learning_rate" \
    --lora-r "$lora_r" \
    --lora-alpha "$lora_alpha" \
    --lora-dropout "$lora_dropout" \
    --per-device-train-batch-size "$batch" \
    --gradient-accumulation-steps "$grad_accum" \
    > "$log_dir/${log_name}.log" 2>&1
  local code=$?
  record_exit "$log_name" "$code"
  echo "[train-fallback] ${label} exit=${code}"
  return "$code"
}

run_train "primary" "$primary_batch" "$primary_grad_accum"
primary_code=$?
if [[ "$primary_code" -eq 0 ]]; then
  exit 0
fi

if [[ "$primary_code" -eq 88 ]]; then
  echo "[train-fallback] primary reported OOM; retrying fallback batch=${fallback_batch} grad_accum=${fallback_grad_accum}"
  run_train "fallback_after_oom" "$fallback_batch" "$fallback_grad_accum"
  exit $?
fi

echo "[train-fallback] primary failed with non-OOM exit=${primary_code}; no fallback attempted"
exit "$primary_code"
