# 3B Model Service Architecture

## Service Boundary

The ClearRead 3B service receives already chunked text blocks and returns one ordered set of summary results.

```text
Project backend
  -> FastAPI wrapper service, port 8010
  -> private Docker network
  -> vLLM OpenAI-compatible server, port 8000
  -> Llama 3.2 3B base model with QLoRA adapter
```

The wrapper service provides:

- API key authentication.
- Request size and block-count validation.
- Concurrent fan-out for valid text blocks.
- Per-block error handling.
- Lightweight JSON response validation.
- Metadata-level service logging.

vLLM provides:

- GPU-backed inference on NVIDIA L4.
- OpenAI-compatible chat completion serving.
- LoRA adapter loading.
- Continuous batching for concurrent requests.

## Batch Processing

The backend sends all chunks for a reading request in one API call. The wrapper creates one asynchronous task per valid block and limits concurrency with `VLLM_MAX_CONCURRENCY=32`. vLLM schedules these requests on the GPU through its serving engine.

The response order follows the input order, so the backend can map each result to the original text block by `id`.
