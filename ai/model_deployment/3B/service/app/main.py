import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status

from app.auth import require_service_api_key
from app.config import Settings, get_settings
from app.response_guard import ResponseGuardError
from app.schemas import ItemError, SummaryMeta, SummaryRequest, SummaryResponse, SummaryResult
from app.vllm_client import VllmClient


logger = logging.getLogger("clearread-ai-summary")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app.state.vllm_client = VllmClient(settings)
    yield
    await app.state.vllm_client.close()


app = FastAPI(title="ClearRead AI Summary", version="v1", lifespan=lifespan)


@app.middleware("http")
async def request_size_guard(request: Request, call_next):
    settings = get_settings()
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.request_body_limit_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail={
                        "code": "request_body_too_large",
                        "message": "Request body exceeds the configured limit.",
                    },
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "invalid_request", "message": "Invalid Content-Length header."},
            ) from None
    return await call_next(request)


@app.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    return {"status": "ok", "service": settings.service_name}


@app.get("/ready")
async def ready(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    vllm_ready = await request.app.state.vllm_client.ready()
    if not vllm_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "model_not_ready", "message": "vLLM backend is not ready."},
        )
    return {
        "status": "ready",
        "service": settings.service_name,
        "model": settings.public_model_name,
        "version": settings.service_version,
    }


@app.post(
    "/v1/clearread/summarize",
    response_model=SummaryResponse,
    dependencies=[Depends(require_service_api_key)],
)
async def summarize(
    payload: SummaryRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SummaryResponse:
    _enforce_content_length(request, settings)
    started = time.perf_counter()
    request_id = payload.requestId or f"reading-{uuid.uuid4()}"
    request_id = request_id.strip()

    _validate_request(payload, settings)
    results = await _summarize_items(payload, request, settings)
    status_value = "ok" if all(item.status == "ok" for item in results) else "partial_error"

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "summary_request_complete request_id=%s item_count=%s status=%s elapsed_ms=%s",
        request_id,
        len(payload.texts),
        status_value,
        elapsed_ms,
    )

    return SummaryResponse(
        requestId=request_id,
        status=status_value,
        results=results,
        errors=[],
        meta=SummaryMeta(
            service=settings.service_name,
            version=settings.service_version,
            model=settings.public_model_name,
        ),
    )


def _enforce_content_length(request: Request, settings: Settings) -> None:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.request_body_limit_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "request_body_too_large",
                "message": "Request body exceeds the configured limit.",
            },
        )


def _validate_request(payload: SummaryRequest, settings: Settings) -> None:
    if not payload.texts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_request", "message": "texts must contain at least one item."},
        )
    if len(payload.texts) > settings.max_blocks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_request", "message": "Too many text blocks."},
        )

    seen: set[str] = set()
    for item in payload.texts:
        if item.id in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_request", "message": "texts[].id must be unique."},
            )
        seen.add(item.id)


async def _summarize_items(
    payload: SummaryRequest, request: Request, settings: Settings
) -> list[SummaryResult]:
    tasks = [
        _summarize_or_error(item.id, item.text, request, settings)
        for item in payload.texts
    ]
    return list(await asyncio.gather(*tasks))


async def _summarize_or_error(
    block_id: str, text: str, request: Request, settings: Settings
) -> SummaryResult:
    cleaned = text.strip()
    if not cleaned:
        return _error_result(block_id, "empty_text", "Text must not be empty.", retryable=False)
    if len(cleaned) > settings.max_chars_per_block:
        return _error_result(
            block_id,
            "text_too_large",
            "Text block exceeds the configured character limit.",
            retryable=False,
        )

    try:
        guarded = await request.app.state.vllm_client.summarize_one(cleaned)
        return SummaryResult(
            id=block_id,
            status="ok",
            summary=guarded.summary,
            keyPoints=guarded.key_points,
            schemaGuardAction=guarded.action,
        )
    except (ResponseGuardError, ValueError) as error:
        return _error_result(
            block_id,
            "model_schema_error",
            _safe_error_message("Model output was not valid summary JSON.", error, settings),
            retryable=True,
        )
    except (httpx.TimeoutException, httpx.ConnectError) as error:
        return _error_result(
            block_id,
            "model_timeout_or_unavailable",
            _safe_error_message("Model backend timed out or was unavailable.", error, settings),
            retryable=True,
        )
    except httpx.HTTPStatusError as error:
        return _error_result(
            block_id,
            "model_http_error",
            _safe_error_message("Model backend returned an HTTP error.", error, settings),
            retryable=True,
        )


def _error_result(
    block_id: str, code: str, message: str, retryable: bool
) -> SummaryResult:
    return SummaryResult(
        id=block_id,
        status="error",
        summary="",
        keyPoints=[],
        schemaGuardAction="not_run" if code in {"empty_text", "text_too_large"} else "failed",
        error=ItemError(code=code, message=message, retryable=retryable),
    )


def _safe_error_message(default: str, error: Exception, settings: Settings) -> str:
    if settings.include_error_details:
        return f"{default} Detail: {error}"
    return default
