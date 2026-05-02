#!/usr/bin/env bash
set -euo pipefail

CONCURRENCY="${1:-8}"
MAX_TOKENS="${2:-320}"

cd "$HOME/clearread-app"
source "$HOME/clearread-vllm-env/bin/activate"

set -a
source "$HOME/clearread-runtime.env"
set +a

pid="$(ss -ltnp | awk '$4 ~ /:8010$/ {print $0}' | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | head -1 || true)"
if [[ -n "${pid}" ]]; then
  kill "${pid}" || true
  for _ in $(seq 1 30); do
    if kill -0 "${pid}" 2>/dev/null; then
      sleep 0.5
    else
      break
    fi
  done
fi

export CLEARREAD_AI_RUNTIME=vllm_http
export CLEARREAD_AI_SERVICE_HOST=0.0.0.0
export CLEARREAD_AI_SERVICE_PORT=8010
export CLEARREAD_AI_VLLM_BASE_URL=http://127.0.0.1:8014
export CLEARREAD_AI_VLLM_API_KEY="${CLEARREAD_AI_VLLM_API_KEY:-${CLEARREAD_INTERNAL_VLLM_API_KEY:-}}"
export CLEARREAD_AI_VLLM_MODEL=clearread
export CLEARREAD_AI_VLLM_INTERNAL_CONCURRENCY="${CONCURRENCY}"
export CLEARREAD_AI_VLLM_REQUEST_TIMEOUT_SECONDS=45
export CLEARREAD_AI_REQUEST_TIMEOUT_SECONDS=90
export CLEARREAD_AI_ENABLE_DEBUG_RESPONSES=false
export CLEARREAD_AI_MAX_TEXTS_PER_REQUEST=32
export CLEARREAD_AI_MAX_CHARACTERS_PER_TEXT=11000
export CLEARREAD_AI_MAX_REQUEST_BODY_BYTES=2097152
export CLEARREAD_AI_VLLM_MAX_TOKENS="${MAX_TOKENS}"

nohup python -m uvicorn ai_summary_service.main:app \
  --host 0.0.0.0 \
  --port 8010 \
  --no-access-log \
  > "$HOME/clearread-api.log" 2>&1 &

new_pid="$!"
echo "${new_pid}" > "$HOME/clearread-api.pid"

for _ in $(seq 1 60); do
  status="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/ready || true)"
  if [[ "${status}" == "200" ]]; then
    echo "api_ready pid=${new_pid} concurrency=${CONCURRENCY} max_tokens=${MAX_TOKENS}"
    exit 0
  fi
  sleep 1
done

echo "api_not_ready pid=${new_pid} concurrency=${CONCURRENCY} max_tokens=${MAX_TOKENS}" >&2
tail -80 "$HOME/clearread-api.log" >&2 || true
exit 1
