#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/clearread-ai-summary/deploy"
READY_URL="http://127.0.0.1:8010/ready"
HEALTH_URL="http://127.0.0.1:8010/health"
MAX_ATTEMPTS="${CLEARREAD_READY_ATTEMPTS:-90}"
SLEEP_SECONDS="${CLEARREAD_READY_SLEEP_SECONDS:-10}"

cd "$APP_DIR"

echo "=== ClearRead AI restart/recover ==="
date -Is

echo
echo "=== Existing containers before recovery ==="
sudo docker compose --env-file .env -f docker-compose.prod.yml ps || true

echo
echo "=== GPU before compose recovery ==="
echo "Note: containers use restart=unless-stopped, so vLLM may already be using GPU after VM boot."
nvidia-smi || true

echo
echo "=== Starting/reconciling Docker Compose services ==="
sudo docker compose --env-file .env -f docker-compose.prod.yml up -d

echo
echo "=== Containers ==="
sudo docker compose --env-file .env -f docker-compose.prod.yml ps

echo
echo "=== Health ==="
curl -fsS "$HEALTH_URL" | jq . || true

echo
echo "=== Waiting for model readiness ==="
for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  if curl -fsS "$READY_URL" >/tmp/clearread-ready.json 2>/dev/null; then
    echo "Ready after attempt ${attempt}/${MAX_ATTEMPTS}."
    jq . /tmp/clearread-ready.json || cat /tmp/clearread-ready.json
    echo
    echo "=== Final containers ==="
    sudo docker compose --env-file .env -f docker-compose.prod.yml ps
    echo
    echo "=== GPU after ready ==="
    nvidia-smi || true
    exit 0
  fi

  echo "Not ready yet (${attempt}/${MAX_ATTEMPTS}); waiting ${SLEEP_SECONDS}s..."
  sleep "$SLEEP_SECONDS"
done

echo
echo "Model did not become ready within $((MAX_ATTEMPTS * SLEEP_SECONDS)) seconds."
echo
echo "=== vLLM recent logs ==="
sudo docker compose --env-file .env -f docker-compose.prod.yml logs --tail=160 vllm || true
exit 1
