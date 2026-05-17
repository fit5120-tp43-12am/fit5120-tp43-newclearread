#!/usr/bin/env bash
set -uo pipefail

benchmark_run_id="${1:-}"
judge_run_id="${2:-}"
system_id="${3:-}"

if [[ -z "$benchmark_run_id" || -z "$judge_run_id" || -z "$system_id" ]]; then
  echo "Usage: $0 <benchmark_run_id> <judge_run_id> <system_id>" >&2
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
  return "$code"
}

run_logged() {
  local name="$1"
  shift
  echo "[final-benchmark] $name"
  "$@" > "$log_dir/${name}_${stamp}.log" 2>&1
  local code=$?
  record_exit "$name" "$code"
  return "$code"
}

run_logged "final_prepare_judge_inputs_${system_id}" \
  python scripts/prepare_final_benchmark_judge_inputs.py \
    --benchmark-run-id "$benchmark_run_id" \
    --judge-run-id "$judge_run_id" \
    --system-id "$system_id" || exit $?

run_logged "final_judge_validate_only_${system_id}" \
  python scripts/run_judge_api.py \
    --judge-run-id "$judge_run_id" \
    --model-key "$system_id" \
    --validate-only || exit $?

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is unavailable; stopping after judge input validation." >&2
  record_exit "final_judge_api_blocked_no_openai_key_${system_id}" 3
  exit 3
fi

if ! run_logged "final_judge_api_${system_id}" \
  python scripts/run_judge_api.py \
    --judge-run-id "$judge_run_id" \
    --model-key "$system_id"; then
  run_logged "final_judge_api_${system_id}_retry_failures" \
    python scripts/run_judge_api.py \
      --judge-run-id "$judge_run_id" \
      --model-key "$system_id" \
      --retry-failures || true
fi

run_logged "final_aggregate_judge_scores_${system_id}" \
  python scripts/aggregate_judge_scores.py \
    --judge-run-id "$judge_run_id" || exit $?

echo "[final-benchmark] completed for ${system_id}"
