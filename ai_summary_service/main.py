from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from json import JSONDecodeError
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .auth import is_authorized
from .config import ServiceSettings
from .logging_utils import configure_logging, log_request_summary
from .runtime import RuntimeLoadError, SummaryRuntime, build_runtime
from .schemas import (
    ItemError,
    PublicError,
    ResponseMeta,
    RuntimeSummaryResult,
    SummaryItemResult,
    SummaryRequest,
    SummaryResponse,
)


class AsyncConcurrencyLimiter:
    def __init__(self, limit: int):
        self._limit = max(1, limit)
        self._active = 0
        self._lock = asyncio.Lock()

    async def try_acquire(self) -> bool:
        async with self._lock:
            if self._active >= self._limit:
                return False
            self._active += 1
            return True

    async def release(self) -> None:
        async with self._lock:
            self._active = max(0, self._active - 1)


def create_app(
    settings: ServiceSettings | None = None,
    runtime: SummaryRuntime | None = None,
) -> FastAPI:
    app_settings = settings or ServiceSettings.from_env()
    logger = configure_logging()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info(
            "service_start service=%s version=%s runtime=%s",
            app_settings.service_name,
            app_settings.version,
            app_settings.runtime,
        )
        yield
        logger.info("service_stop service=%s", app_settings.service_name)

    app = FastAPI(
        title="ClearRead AI Summary Service",
        version=app_settings.version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.runtime = runtime or build_runtime(app_settings)
    app.state.limiter = AsyncConcurrencyLimiter(app_settings.max_concurrent_requests)
    app.state.logger = logger

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": app_settings.service_name}

    @app.get("/ready", response_model=None)
    async def ready():
        if not app_settings.has_api_key:
            return _not_ready_response(app_settings)
        try:
            await app.state.runtime.ensure_loaded()
        except RuntimeLoadError:
            return _not_ready_response(app_settings)
        except Exception:
            return _not_ready_response(app_settings)

        return {
            "status": "ready",
            "service": app_settings.service_name,
            "model": app_settings.model_label,
            "version": app_settings.version,
        }

    @app.post("/v1/clearread/summarize", response_model=None)
    async def summarize(request: Request) -> JSONResponse:
        started = time.perf_counter()

        if not is_authorized(request.headers.get("authorization"), app_settings):
            return _whole_error_response(
                app_settings,
                401,
                None,
                "unauthorized",
                "Missing or invalid API key.",
                "authorization",
                False,
                logger=app.state.logger,
                started=started,
            )

        content_type = request.headers.get("content-type", "")
        if content_type.split(";")[0].strip().lower() != "application/json":
            return _whole_error_response(
                app_settings,
                415,
                None,
                "unsupported_media_type",
                "Content-Type must be application/json.",
                "content-type",
                False,
                logger=app.state.logger,
                started=started,
            )

        if _content_length_too_large(request, app_settings):
            return _whole_error_response(
                app_settings,
                413,
                None,
                "request_body_too_large",
                "Request body exceeds the maximum allowed size.",
                "body",
                False,
                logger=app.state.logger,
                started=started,
            )

        try:
            raw_body = await request.body()
        except Exception:
            return _whole_error_response(
                app_settings,
                400,
                None,
                "malformed_json",
                "Request body must be valid JSON.",
                "body",
                False,
                logger=app.state.logger,
                started=started,
            )

        if len(raw_body) > app_settings.max_request_body_bytes:
            return _whole_error_response(
                app_settings,
                413,
                None,
                "request_body_too_large",
                "Request body exceeds the maximum allowed size.",
                "body",
                False,
                logger=app.state.logger,
                started=started,
            )

        try:
            payload = json.loads(raw_body)
        except (JSONDecodeError, json.JSONDecodeError):
            return _whole_error_response(
                app_settings,
                400,
                None,
                "malformed_json",
                "Request body must be valid JSON.",
                "body",
                False,
                logger=app.state.logger,
                started=started,
            )

        request_id = _extract_request_id(payload)
        payload_item_ids, payload_text_lengths = _payload_log_metadata(payload)
        try:
            summary_request = SummaryRequest.model_validate(payload)
        except ValidationError:
            return _whole_error_response(
                app_settings,
                422,
                request_id,
                "invalid_request",
                "The request body does not match the ClearRead summary schema.",
                "body",
                False,
                logger=app.state.logger,
                started=started,
                item_ids=payload_item_ids,
                text_lengths=payload_text_lengths,
            )

        validation_error = _validate_request(summary_request, app_settings)
        if validation_error:
            item_ids, text_lengths = _summary_request_log_metadata(summary_request)
            return _whole_error_response(
                app_settings,
                422,
                summary_request.request_id,
                "invalid_request",
                validation_error,
                "texts",
                False,
                logger=app.state.logger,
                started=started,
                item_ids=item_ids,
                text_lengths=text_lengths,
            )

        acquired = await app.state.limiter.try_acquire()
        if not acquired:
            item_ids, text_lengths = _summary_request_log_metadata(summary_request)
            return _whole_error_response(
                app_settings,
                429,
                summary_request.request_id,
                "too_many_requests",
                "The AI summary service is already processing the maximum number of requests.",
                "concurrency",
                True,
                logger=app.state.logger,
                started=started,
                item_ids=item_ids,
                text_lengths=text_lengths,
            )

        try:
            response = await asyncio.wait_for(
                _process_summary_request(app, summary_request),
                timeout=app_settings.request_timeout_seconds,
            )
        except RuntimeLoadError:
            return _whole_error_response(
                app_settings,
                503,
                summary_request.request_id,
                "service_not_ready",
                "The model service is starting or unavailable.",
                "runtime",
                True,
                logger=app.state.logger,
                started=started,
                item_ids=_summary_request_log_metadata(summary_request)[0],
                text_lengths=_summary_request_log_metadata(summary_request)[1],
            )
        except asyncio.TimeoutError:
            response = _summary_response(
                app_settings,
                summary_request.request_id,
                "error",
                [],
                [
                    PublicError(
                        code="request_timeout",
                        message="The summary request exceeded the configured timeout.",
                        retryable=True,
                        target="request",
                    )
                ],
            )
            _log_whole_request_error(
                app.state.logger,
                summary_request.request_id,
                *_summary_request_log_metadata(summary_request),
                code="request_timeout",
                started=started,
            )
            return JSONResponse(
                status_code=504,
                content=_response_content(response),
            )
        except Exception:
            item_ids, text_lengths = _summary_request_log_metadata(summary_request)
            return _whole_error_response(
                app_settings,
                500,
                summary_request.request_id,
                "internal_error",
                "The summary request failed because of an internal service error.",
                "request",
                True,
                logger=app.state.logger,
                started=started,
                item_ids=item_ids,
                text_lengths=text_lengths,
            )
        finally:
            await app.state.limiter.release()

        latency_ms = int((time.perf_counter() - started) * 1000)
        _log_completed_request(app, summary_request, response, latency_ms)
        return JSONResponse(status_code=200, content=_response_content(response))

    return app


async def _process_summary_request(
    app: FastAPI,
    summary_request: SummaryRequest,
) -> SummaryResponse:
    settings: ServiceSettings = app.state.settings
    runtime: SummaryRuntime = app.state.runtime

    await runtime.ensure_loaded()

    include_debug = (
        summary_request.options.include_debug and settings.enable_debug_responses
    )
    results: list[SummaryItemResult | None] = [None] * len(summary_request.texts)
    runtime_items: list[tuple[int, str, str]] = []

    for index, item in enumerate(summary_request.texts):
        input_error = _validate_item_input(settings, item.id, item.text, include_debug)
        if input_error is not None:
            results[index] = input_error
        else:
            runtime_items.append((index, item.id, item.text))

    if runtime_items:
        runtime_results = await _summarize_runtime_items(
            runtime,
            settings,
            runtime_items,
            include_debug,
        )
        for (index, item_id, _), runtime_result in zip(runtime_items, runtime_results):
            results[index] = _runtime_to_item(item_id, runtime_result)

    completed_results = [result for result in results if result is not None]
    status = _top_level_status(completed_results)
    return _summary_response(settings, summary_request.request_id, status, completed_results, [])


async def _summarize_runtime_items(
    runtime: SummaryRuntime,
    settings: ServiceSettings,
    runtime_items: list[tuple[int, str, str]],
    include_debug: bool,
) -> list[RuntimeSummaryResult]:
    if settings.runtime == "vllm_http":
        return await asyncio.gather(
            *[
                runtime.summarize(text, include_debug)
                for _, _, text in runtime_items
            ]
        )

    results: list[RuntimeSummaryResult] = []
    for _, _, text in runtime_items:
        results.append(await runtime.summarize(text, include_debug))
    return results


def _validate_item_input(
    settings: ServiceSettings,
    item_id: str,
    text: str,
    include_debug: bool,
) -> SummaryItemResult | None:
    if not text.strip():
        return _item_error(
            item_id,
            "empty_text",
            "Text must not be empty.",
            False,
            "not_run",
            _input_debug(include_debug, settings.runtime, len(text)),
        )

    if len(text) > settings.max_characters_per_text:
        return _item_error(
            item_id,
            "text_too_large",
            "Text exceeds the maximum allowed character count.",
            False,
            "not_run",
            _input_debug(include_debug, settings.runtime, len(text)),
        )

    return None


def _runtime_to_item(item_id: str, runtime_result: RuntimeSummaryResult) -> SummaryItemResult:
    if runtime_result.status == "ok":
        return SummaryItemResult(
            id=item_id,
            status="ok",
            summary=runtime_result.summary,
            keyPoints=runtime_result.key_points,
            schemaGuardAction=runtime_result.schema_guard_action,
            debug=runtime_result.debug,
        )

    return SummaryItemResult(
        id=item_id,
        status="error",
        summary="",
        keyPoints=[],
        schemaGuardAction=runtime_result.schema_guard_action,
        error=runtime_result.error
        or ItemError(
            code="model_runtime_error",
            message="The model runtime failed while processing this item.",
            retryable=True,
        ),
        debug=runtime_result.debug,
    )


def _validate_request(request: SummaryRequest, settings: ServiceSettings) -> str | None:
    if not request.texts:
        return "texts must contain at least one item."
    if len(request.texts) > settings.max_texts_per_request:
        return f"texts must contain 1 to {settings.max_texts_per_request} items."

    item_ids = [item.id for item in request.texts]
    if len(item_ids) != len(set(item_ids)):
        return "Each text item must have a unique non-empty id."

    return None


def _top_level_status(results: list[SummaryItemResult]) -> str:
    ok_count = sum(1 for result in results if result.status == "ok")
    if ok_count == len(results):
        return "ok"
    if ok_count > 0:
        return "partial_error"
    return "error"


def _summary_response(
    settings: ServiceSettings,
    request_id: str | None,
    status: str,
    results: list[SummaryItemResult],
    errors: list[PublicError],
) -> SummaryResponse:
    return SummaryResponse(
        requestId=request_id,
        status=status,
        results=results,
        errors=errors,
        meta=ResponseMeta(
            service=settings.service_name,
            version=settings.version,
            model=settings.model_label,
        ),
    )


def _whole_error_response(
    settings: ServiceSettings,
    http_status: int,
    request_id: str | None,
    code: str,
    message: str,
    target: str,
    retryable: bool,
    logger: Any | None = None,
    started: float | None = None,
    item_ids: list[str] | None = None,
    text_lengths: list[int] | None = None,
) -> JSONResponse:
    response = _summary_response(
        settings,
        request_id,
        "error",
        [],
        [PublicError(code=code, message=message, target=target, retryable=retryable)],
    )
    if logger is not None and started is not None:
        _log_whole_request_error(
            logger,
            request_id,
            item_ids or [],
            text_lengths or [],
            code,
            started,
        )
    return JSONResponse(status_code=http_status, content=_response_content(response))


def _not_ready_response(settings: ServiceSettings) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "service": settings.service_name,
            "version": settings.version,
            "error": {
                "code": "model_not_loaded",
                "message": "The model service is starting or unavailable.",
            },
        },
    )


def _item_error(
    item_id: str,
    code: str,
    message: str,
    retryable: bool,
    schema_guard_action: str,
    debug: dict[str, Any] | None = None,
) -> SummaryItemResult:
    return SummaryItemResult(
        id=item_id,
        status="error",
        summary="",
        keyPoints=[],
        schemaGuardAction=schema_guard_action,
        error=ItemError(code=code, message=message, retryable=retryable),
        debug=debug,
    )


def _input_debug(
    include_debug: bool,
    runtime: str,
    input_characters: int,
) -> dict[str, Any] | None:
    if not include_debug:
        return None
    return {
        "inputCharacters": input_characters,
        "latencyMs": 0,
        "runtime": runtime,
        "schemaErrors": [],
    }


def _extract_request_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    request_id = payload.get("requestId")
    if isinstance(request_id, str) and len(request_id) <= 128:
        return request_id
    return None


def _content_length_too_large(request: Request, settings: ServiceSettings) -> bool:
    content_length = request.headers.get("content-length")
    if not content_length:
        return False
    try:
        return int(content_length) > settings.max_request_body_bytes
    except ValueError:
        return False


def _payload_log_metadata(payload: Any) -> tuple[list[str], list[int]]:
    if not isinstance(payload, dict):
        return [], []
    texts = payload.get("texts")
    if not isinstance(texts, list):
        return [], []

    item_ids: list[str] = []
    text_lengths: list[int] = []
    for item in texts:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        text = item.get("text")
        if isinstance(item_id, str):
            item_ids.append(item_id[:128])
        if isinstance(text, str):
            text_lengths.append(len(text))
    return item_ids, text_lengths


def _summary_request_log_metadata(
    summary_request: SummaryRequest,
) -> tuple[list[str], list[int]]:
    return (
        [item.id for item in summary_request.texts],
        [len(item.text) for item in summary_request.texts],
    )


def _log_whole_request_error(
    logger: Any,
    request_id: str | None,
    item_ids: list[str],
    text_lengths: list[int],
    code: str,
    started: float,
) -> None:
    latency_ms = int((time.perf_counter() - started) * 1000)
    log_request_summary(
        logger,
        request_id,
        item_ids,
        text_lengths,
        "error",
        latency_ms,
        [code],
    )


def _response_content(response: SummaryResponse) -> dict[str, Any]:
    content = response.model_dump(by_alias=True)
    for result in content.get("results", []):
        if result.get("error") is None:
            result.pop("error", None)
        if result.get("debug") is None:
            result.pop("debug", None)
    for error in content.get("errors", []):
        if error.get("target") is None:
            error.pop("target", None)
    return content


def _log_completed_request(
    app: FastAPI,
    summary_request: SummaryRequest,
    response: SummaryResponse,
    latency_ms: int,
) -> None:
    error_codes: list[str] = []
    for result in response.results:
        if result.error:
            error_codes.append(result.error.code)
    for error in response.errors:
        error_codes.append(error.code)

    log_request_summary(
        app.state.logger,
        summary_request.request_id,
        [item.id for item in summary_request.texts],
        [len(item.text) for item in summary_request.texts],
        response.status,
        latency_ms,
        error_codes,
    )


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = ServiceSettings.from_env()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=False,
    )
