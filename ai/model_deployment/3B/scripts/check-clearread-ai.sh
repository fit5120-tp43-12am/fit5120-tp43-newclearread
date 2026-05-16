#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/clearread-ai-summary/deploy"
cd "$APP_DIR"

echo "=== ClearRead AI status check ==="
date -Is

echo
echo "=== Docker containers ==="
sudo docker compose --env-file .env -f docker-compose.prod.yml ps

echo
echo "=== Local health ==="
curl -s http://127.0.0.1:8010/health | jq . || true

echo
echo "=== Local ready ==="
curl -s http://127.0.0.1:8010/ready | jq . || true

echo
echo "=== Runtime limits ==="
sudo docker compose --env-file .env -f docker-compose.prod.yml exec -T clearread-summary-api python - <<'PY' || true
from app.config import get_settings

s = get_settings()
for key in [
    "request_body_limit_bytes",
    "max_blocks",
    "max_chars_per_block",
    "vllm_timeout_seconds",
    "vllm_max_concurrency",
    "vllm_max_tokens",
    "public_model_name",
    "vllm_model",
]:
    print(f"{key}={getattr(s, key)}")
print(f"request_body_limit_mb={s.request_body_limit_bytes / 1024 / 1024:.2f}")
PY

echo
echo "=== vLLM startup markers / recent errors ==="
sudo docker compose --env-file .env -f docker-compose.prod.yml logs --tail=220 vllm \
  | grep -E "Loaded new LoRA adapter|Starting vLLM server|Application startup complete|ERROR|Traceback|CUDA|Loading weights|Avg prompt throughput|Avg generation throughput" \
  || true

echo
echo "=== GPU ==="
nvidia-smi || true
