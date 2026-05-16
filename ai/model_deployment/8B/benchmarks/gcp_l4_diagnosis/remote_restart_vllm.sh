#!/usr/bin/env bash
set -euo pipefail

ENFORCE_EAGER="${1:-true}"
GPU_MEMORY_UTILIZATION="${2:-0.78}"
MAX_NUM_SEQS="${3:-16}"

source "$HOME/clearread-vllm-env/bin/activate"
set -a
source "$HOME/clearread-runtime.env"
set +a

VLLM_KEY="${CLEARREAD_INTERNAL_VLLM_API_KEY:-${CLEARREAD_AI_VLLM_API_KEY:-}}"
if [[ -z "${VLLM_KEY}" ]]; then
  echo "vllm_key_missing" >&2
  exit 1
fi

api_pid="$(ss -ltnp | awk '$4 ~ /:8010$/ {print $0}' | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | head -1 || true)"
if [[ -n "${api_pid}" ]]; then
  kill "${api_pid}" || true
fi

vllm_pid="$(ss -ltnp | awk '$4 ~ /127\.0\.0\.1:8014$/ {print $0}' | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | head -1 || true)"
if [[ -n "${vllm_pid}" ]]; then
  kill "${vllm_pid}" || true
  for _ in $(seq 1 60); do
    if ss -ltnp | grep -q '127.0.0.1:8014'; then
      sleep 1
    else
      break
    fi
  done
fi

export VLLM_USE_FLASHINFER_SAMPLER=0

command=(
  python -m vllm.entrypoints.openai.api_server
  --host 127.0.0.1
  --port 8014
  --model unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
  --trust-remote-code
  --dtype bfloat16
  --max-model-len 3072
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}"
  --enable-lora
  --max-lora-rank 16
  --max-loras 1
  --lora-modules "clearread=${ADAPTER_DIR}"
  --served-model-name clearread
  --no-enable-log-requests
  --disable-log-stats
  --disable-uvicorn-access-log
  --disable-fastapi-docs
  --max-num-seqs "${MAX_NUM_SEQS}"
  --api-key "${VLLM_KEY}"
)

if [[ "${ENFORCE_EAGER}" == "true" ]]; then
  command+=(--enforce-eager)
fi

nohup "${command[@]}" > "$HOME/clearread-vllm.log" 2>&1 &
new_pid="$!"
echo "${new_pid}" > "$HOME/clearread-vllm.pid"

for attempt in $(seq 1 180); do
  status="$(
    curl -s -o /dev/null \
      -H "Authorization: Bearer ${VLLM_KEY}" \
      -w '%{http_code}' \
      http://127.0.0.1:8014/v1/models || true
  )"
  if [[ "${status}" == "200" ]]; then
    echo "vllm_ready pid=${new_pid} enforce_eager=${ENFORCE_EAGER} gpu_memory_utilization=${GPU_MEMORY_UTILIZATION} max_num_seqs=${MAX_NUM_SEQS} attempt=${attempt}"
    nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,power.draw,power.limit,temperature.gpu --format=csv,noheader
    exit 0
  fi
  if ! kill -0 "${new_pid}" 2>/dev/null; then
    echo "vllm_process_exited pid=${new_pid} enforce_eager=${ENFORCE_EAGER}" >&2
    sed -E 's/(--api-key )[[:graph:]]+/\1REDACTED/g; s/(api_key=)[^,) ]+/\1REDACTED/g' "$HOME/clearread-vllm.log" | tail -80 >&2 || true
    exit 1
  fi
  sleep 2
done

echo "vllm_not_ready pid=${new_pid} enforce_eager=${ENFORCE_EAGER}" >&2
sed -E 's/(--api-key )[[:graph:]]+/\1REDACTED/g; s/(api_key=)[^,) ]+/\1REDACTED/g' "$HOME/clearread-vllm.log" | tail -80 >&2 || true
exit 1
