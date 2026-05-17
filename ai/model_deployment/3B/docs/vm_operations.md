# VM Operations

## VM Details

```text
GCP project: clearead-junwei
Instance: instance-20260516-075135
Zone: asia-southeast1-c
External IP: 34.21.166.229
Machine type: g2-standard-4
GPU: 1 x NVIDIA L4
Runtime root: /opt/clearread-ai-summary
```

## Standard Status Check

After VM startup, SSH into the VM and run:

```bash
~/check-clearread-ai.sh
```

The expected readiness state is:

```json
{
  "status": "ready",
  "service": "clearread-ai-summary",
  "model": "clearread-llama32-3b-qlora-phase2-r32-a64-lr1p5e4-epoch4",
  "version": "v1"
}
```

## Recovery Command

If the status check shows the model is still loading, wait a few minutes and repeat the status check. If service recovery is required, run:

```bash
~/restart-clearread-ai.sh
~/check-clearread-ai.sh
```

## Runtime Notes

The Docker containers use `restart=unless-stopped`. After VM boot, Docker starts the wrapper and vLLM services automatically. GPU memory usage by `VLLM::EngineCore` after startup is expected.

## Direct Commands

```bash
cd /opt/clearread-ai-summary/deploy
sudo docker compose --env-file .env -f docker-compose.prod.yml ps
curl -s http://127.0.0.1:8010/health | jq .
curl -s http://127.0.0.1:8010/ready | jq .
nvidia-smi
```
