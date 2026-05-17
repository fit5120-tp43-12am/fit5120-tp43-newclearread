#!/usr/bin/env bash
set -uo pipefail

candidate_key="${1:-}"
run_id="${2:-}"
stage_label="${3:-}"
judge_run_id="${4:-}"
epochs="${5:-1 2 3 4 5}"

if [[ -z "$candidate_key" || -z "$run_id" || -z "$stage_label" || -z "$judge_run_id" ]]; then
  echo "Usage: $0 <candidate_key> <run_id> <stage_label> <judge_run_id> [epochs]" >&2
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
  echo "[compressed-postprocess] $name"
  "$@" > "$log_dir/${name}_${stamp}.log" 2>&1
  local code=$?
  record_exit "$name" "$code"
  return "$code"
}

read -r -a epoch_array <<< "$epochs"

for epoch in "${epoch_array[@]}"; do
  metrics_path="model_workspaces/${candidate_key}/outputs/validation/${run_id}_epoch_${epoch}_record_messages/metrics.json"
  if [[ -f "$metrics_path" ]]; then
    echo "[compressed-postprocess] validation already exists for epoch ${epoch}; skipping validation"
    continue
  fi
  run_logged "${stage_label}_validate_${candidate_key}_epoch${epoch}" \
    python scripts/validate_sweep_adapter.py \
      --candidate-key "$candidate_key" \
      --train-run-id "$run_id" \
      --epoch "$epoch" \
      --allow-overwrite || exit $?
done

selected_epochs="$(
  python scripts/select_validation_top_epochs.py \
    --candidate-key "$candidate_key" \
    --train-run-id "$run_id" \
    --epochs "${epoch_array[@]}"
)"
read -r -a selected_epoch_array <<< "$selected_epochs"
if [[ "${#selected_epoch_array[@]}" -eq 0 ]]; then
  echo "No selected epochs for judge scoring." >&2
  exit 4
fi
echo "[compressed-postprocess] selected judge epochs: ${selected_epochs}"

run_logged "${stage_label}_semantic_rescue_${candidate_key}" \
  python scripts/semantic_rescue_validation_sample.py \
    --candidate-key "$candidate_key" \
    --train-run-id "$run_id" \
    --epochs "${selected_epoch_array[@]}" || exit $?

run_logged "${stage_label}_prepare_val50_judge_inputs_${candidate_key}" \
  python scripts/prepare_validation_judge_inputs.py \
    --candidate-key "$candidate_key" \
    --train-run-id "$run_id" \
    --epochs "${selected_epoch_array[@]}" \
    --judge-run-id "$judge_run_id" \
    --stage-label "$stage_label" || exit $?

for epoch in "${selected_epoch_array[@]}"; do
  model_key="${candidate_key}_${stage_label}_epoch_${epoch}"
  run_logged "${stage_label}_judge_validate_only_${model_key}" \
    python scripts/run_judge_api.py \
      --judge-run-id "$judge_run_id" \
      --model-key "$model_key" \
      --validate-only || exit $?
done

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is unavailable; stopping after judge input validation." >&2
  record_exit "${stage_label}_judge_api_blocked_no_openai_key_${candidate_key}" 3
  exit 3
fi

for epoch in "${selected_epoch_array[@]}"; do
  model_key="${candidate_key}_${stage_label}_epoch_${epoch}"
  if ! run_logged "${stage_label}_judge_api_${model_key}" \
    python scripts/run_judge_api.py \
      --judge-run-id "$judge_run_id" \
      --model-key "$model_key"; then
    if ! run_logged "${stage_label}_judge_api_${model_key}_retry_failures" \
      python scripts/run_judge_api.py \
        --judge-run-id "$judge_run_id" \
        --model-key "$model_key" \
        --retry-failures; then
      echo "[compressed-postprocess] warning: judge retry returned nonzero for ${model_key}; continuing." >&2
      record_exit "${stage_label}_judge_api_${model_key}_nonzero_continued" 1 || true
    fi
  fi
done

run_logged "${stage_label}_aggregate_judge_scores_${candidate_key}" \
  python scripts/aggregate_judge_scores.py \
    --judge-run-id "$judge_run_id" || exit $?

run_logged "${stage_label}_select_checkpoint_${candidate_key}" \
  python scripts/select_run_checkpoint.py \
    --candidate-key "$candidate_key" \
    --run-id "$run_id" \
    --stage-label "$stage_label" \
    --epochs "${selected_epoch_array[@]}" || exit $?

echo "[compressed-postprocess] completed for ${candidate_key} / ${run_id}"
