#!/usr/bin/env bash
set -uo pipefail

candidate_key="${1:-}"
judge_run_id="${2:-}"
run_id="${3:-stage1_anchor_r32_lr2e4}"

if [[ -z "$candidate_key" || -z "$judge_run_id" ]]; then
  echo "Usage: $0 <candidate_key> <judge_run_id> [run_id]" >&2
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
  echo "[stage1-postprocess] $name"
  "$@" > "$log_dir/${name}_${stamp}.log" 2>&1
  local code=$?
  record_exit "$name" "$code"
  return "$code"
}

for epoch in 1 2 3 4 5; do
  run_logged "stage1_validate_${candidate_key}_epoch${epoch}" \
    python scripts/validate_sweep_adapter.py \
      --candidate-key "$candidate_key" \
      --train-run-id "$run_id" \
      --epoch "$epoch" \
      --allow-overwrite || exit $?
done

run_logged "stage1_semantic_rescue_${candidate_key}" \
  python scripts/semantic_rescue_validation_sample.py \
    --candidate-key "$candidate_key" \
    --train-run-id "$run_id" \
    --epochs 1 2 3 4 5 || exit $?

run_logged "stage1_prepare_val50_judge_inputs_${candidate_key}" \
  python scripts/prepare_validation_judge_inputs.py \
    --candidate-key "$candidate_key" \
    --train-run-id "$run_id" \
    --epochs 1 2 3 4 5 \
    --judge-run-id "$judge_run_id" || exit $?

for epoch in 1 2 3 4 5; do
  model_key="${candidate_key}_stage1_epoch_${epoch}"
  run_logged "stage1_judge_validate_only_${model_key}" \
    python scripts/run_judge_api.py \
      --judge-run-id "$judge_run_id" \
      --model-key "$model_key" \
      --validate-only || exit $?
done

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is unavailable; stopping after judge input validation." >&2
  record_exit "stage1_judge_api_blocked_no_openai_key_${candidate_key}" 3
  exit 3
fi

for epoch in 1 2 3 4 5; do
  model_key="${candidate_key}_stage1_epoch_${epoch}"
  if ! run_logged "stage1_judge_api_${model_key}" \
    python scripts/run_judge_api.py \
      --judge-run-id "$judge_run_id" \
      --model-key "$model_key"; then
    if ! run_logged "stage1_judge_api_${model_key}_retry_failures" \
      python scripts/run_judge_api.py \
        --judge-run-id "$judge_run_id" \
        --model-key "$model_key" \
        --retry-failures; then
      echo "[stage1-postprocess] warning: judge retry returned nonzero for ${model_key}; continuing so later epochs are still recorded." >&2
      record_exit "stage1_judge_api_${model_key}_nonzero_continued" 1 || true
    fi
  fi
done

run_logged "stage1_aggregate_judge_scores_${candidate_key}" \
  python scripts/aggregate_judge_scores.py \
    --judge-run-id "$judge_run_id" || exit $?

run_logged "stage1_select_checkpoint_${candidate_key}" \
  python scripts/select_stage1_checkpoint.py \
    --candidate-key "$candidate_key" || exit $?

run_logged "stage1_summarize_results_after_${candidate_key}" \
  python scripts/summarize_stage1_results.py || exit $?

echo "[stage1-postprocess] completed for ${candidate_key}"
