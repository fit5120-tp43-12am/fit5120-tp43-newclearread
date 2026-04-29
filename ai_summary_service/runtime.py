from __future__ import annotations

import asyncio
import importlib.util
import inspect
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

from .config import ServiceSettings
from .schemas import ItemError, RuntimeSummaryResult


class SummaryRuntime(Protocol):
    async def ensure_loaded(self) -> None:
        ...

    async def summarize(self, text: str, include_debug: bool) -> RuntimeSummaryResult:
        ...


class RuntimeLoadError(Exception):
    """Raised when the configured model runtime cannot become ready."""


def build_runtime(settings: ServiceSettings) -> SummaryRuntime:
    if settings.runtime == "mock":
        return MockSummaryRuntime(settings)
    if settings.runtime == "transformers":
        return TransformersSummaryRuntime(settings)
    raise RuntimeLoadError("Unsupported AI summary runtime.")


class MockSummaryRuntime:
    """Deterministic runtime used by tests and local contract checks."""

    def __init__(self, settings: ServiceSettings):
        self._settings = settings
        self._loaded = False

    async def ensure_loaded(self) -> None:
        self._loaded = True

    async def summarize(self, text: str, include_debug: bool) -> RuntimeSummaryResult:
        await self.ensure_loaded()
        started = time.perf_counter()

        if "MOCK_SCHEMA_ERROR" in text:
            return RuntimeSummaryResult(
                status="error",
                summary="",
                key_points=[],
                schema_guard_action="return_error_object",
                error=ItemError(
                    code="model_schema_error",
                    message="The model output could not be converted into a valid summary.",
                    retryable=False,
                ),
                debug=_safe_debug(
                    include_debug,
                    self._settings.runtime,
                    len(text),
                    started,
                    schema_errors=["mock_schema_error"],
                ),
            )

        if "MOCK_RUNTIME_ERROR" in text:
            return RuntimeSummaryResult(
                status="error",
                summary="",
                key_points=[],
                schema_guard_action="return_error_object",
                error=ItemError(
                    code="model_runtime_error",
                    message="The model runtime failed while processing this item.",
                    retryable=True,
                ),
                debug=_safe_debug(
                    include_debug,
                    self._settings.runtime,
                    len(text),
                    started,
                    schema_errors=[],
                ),
            )

        return RuntimeSummaryResult(
            status="ok",
            summary="This mock summary confirms the ClearRead service processed the block. It is deterministic for contract testing.",
            key_points=[
                "The mock runtime returned a valid first key point.",
                "The mock runtime returned a valid second key point.",
                "The mock runtime returned a valid third key point.",
                "The mock runtime returned a valid fourth key point.",
            ],
            schema_guard_action="none",
            debug=_safe_debug(include_debug, self._settings.runtime, len(text), started),
        )


class TransformersSummaryRuntime:
    """Persistent Transformers/Unsloth runtime that reuses the final wrapper module."""

    def __init__(self, settings: ServiceSettings):
        self._settings = settings
        self._load_lock = asyncio.Lock()
        self._loaded = False
        self._wrapper: ModuleType | None = None
        self._model: Any = None
        self._tokenizer: Any = None
        self._config: dict[str, Any] = {}
        self._system_prompt = ""
        self._generation_config: dict[str, Any] = {}

    async def ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with self._load_lock:
            if self._loaded:
                return
            await asyncio.to_thread(self._load_sync)
            self._loaded = True

    async def summarize(self, text: str, include_debug: bool) -> RuntimeSummaryResult:
        await self.ensure_loaded()
        started = time.perf_counter()
        try:
            guarded = await asyncio.to_thread(self._generate_and_guard, text)
        except Exception:
            return RuntimeSummaryResult(
                status="error",
                summary="",
                key_points=[],
                schema_guard_action="return_error_object",
                error=ItemError(
                    code="model_runtime_error",
                    message="The model runtime failed while processing this item.",
                    retryable=True,
                ),
                debug=_safe_debug(include_debug, self._settings.runtime, len(text), started),
            )

        return self._map_guarded_output(guarded, include_debug, len(text), started)

    def _load_sync(self) -> None:
        wrapper_path = _required_path(self._settings.wrapper_path, "wrapper")
        config_path = _required_path(self._settings.inference_config, "inference config")
        wrapper = _import_wrapper(wrapper_path)
        _verify_wrapper(wrapper)

        config = wrapper.load_config(config_path)
        adapter_path = self._resolve_adapter_path(wrapper, config, config_path)
        if not adapter_path.exists():
            raise RuntimeLoadError("Configured model adapter is unavailable.")

        model, tokenizer = wrapper.load_model_with_adapter(
            config,
            adapter_path,
            self._settings.base_model_id or None,
        )

        self._wrapper = wrapper
        self._model = model
        self._tokenizer = tokenizer
        self._config = config
        self._system_prompt = str(
            config.get("prompt", {}).get("system")
            or getattr(wrapper, "DEFAULT_SYSTEM_PROMPT", "")
        )
        self._generation_config = config.get("generation", {})

    def _resolve_adapter_path(
        self,
        wrapper: ModuleType,
        config: dict[str, Any],
        config_path: Path,
    ) -> Path:
        adapter_value = self._settings.adapter_dir or str(
            config.get("artifact", {}).get("adapter_dir") or ""
        )
        if not adapter_value:
            raise RuntimeLoadError("Model adapter path is not configured.")

        adapter_path = Path(adapter_value)
        if adapter_path.is_absolute():
            return adapter_path

        project_root = _config_project_root(config_path)
        if hasattr(wrapper, "resolve_path"):
            return wrapper.resolve_path(project_root, adapter_path)
        return project_root / adapter_path

    def _generate_and_guard(self, text: str) -> dict[str, Any]:
        assert self._wrapper is not None
        raw_output = self._wrapper.generate_raw_text(
            self._model,
            self._tokenizer,
            self._system_prompt,
            text,
            self._generation_config,
            None,
        )
        return self._wrapper.guarded_output(raw_output)

    def _map_guarded_output(
        self,
        guarded: dict[str, Any],
        include_debug: bool,
        input_characters: int,
        started: float,
    ) -> RuntimeSummaryResult:
        schema_errors = guarded.get("errors") if isinstance(guarded.get("errors"), list) else []
        if guarded.get("status") == "ok":
            output = guarded.get("output")
            if not isinstance(output, dict):
                return _schema_error_result(include_debug, self._settings.runtime, input_characters, started)

            summary = output.get("main_idea")
            key_points = output.get("key_points")
            if not isinstance(summary, str) or not _valid_key_points(key_points):
                return _schema_error_result(
                    include_debug,
                    self._settings.runtime,
                    input_characters,
                    started,
                    schema_errors=schema_errors,
                )

            return RuntimeSummaryResult(
                status="ok",
                summary=summary,
                key_points=key_points,
                schema_guard_action=str(guarded.get("schema_guard_action") or "none"),
                debug=_safe_debug(
                    include_debug,
                    self._settings.runtime,
                    input_characters,
                    started,
                    schema_errors=schema_errors,
                ),
            )

        return _schema_error_result(
            include_debug,
            self._settings.runtime,
            input_characters,
            started,
            schema_errors=schema_errors,
            wrapper_error_code=_wrapper_error_code(guarded),
        )


def _safe_debug(
    include_debug: bool,
    runtime: str,
    input_characters: int,
    started: float,
    schema_errors: list[str] | None = None,
    wrapper_error_code: str | None = None,
) -> dict[str, Any] | None:
    if not include_debug:
        return None

    debug: dict[str, Any] = {
        "inputCharacters": input_characters,
        "latencyMs": int((time.perf_counter() - started) * 1000),
        "runtime": runtime,
        "schemaErrors": schema_errors or [],
    }
    if wrapper_error_code:
        debug["wrapperErrorCode"] = wrapper_error_code
    return debug


def _schema_error_result(
    include_debug: bool,
    runtime: str,
    input_characters: int,
    started: float,
    schema_errors: list[str] | None = None,
    wrapper_error_code: str | None = None,
) -> RuntimeSummaryResult:
    return RuntimeSummaryResult(
        status="error",
        summary="",
        key_points=[],
        schema_guard_action="return_error_object",
        error=ItemError(
            code="model_schema_error",
            message="The model output could not be converted into a valid summary.",
            retryable=False,
        ),
        debug=_safe_debug(
            include_debug,
            runtime,
            input_characters,
            started,
            schema_errors=schema_errors,
            wrapper_error_code=wrapper_error_code,
        ),
    )


def _valid_key_points(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 4 and all(
        isinstance(item, str) for item in value
    )


def _required_path(value: str, label: str) -> Path:
    if not value:
        raise RuntimeLoadError(f"The {label} path is not configured.")
    path = Path(value)
    if not path.exists():
        raise RuntimeLoadError(f"The configured {label} path is unavailable.")
    return path


def _import_wrapper(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("clearread_final_inference_wrapper", path)
    if spec is None or spec.loader is None:
        raise RuntimeLoadError("The inference wrapper could not be imported.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verify_wrapper(wrapper: ModuleType) -> None:
    required_functions = {
        "load_config": 1,
        "load_model_with_adapter": 3,
        "generate_raw_text": 6,
        "guarded_output": 1,
    }
    for function_name, expected_min_args in required_functions.items():
        candidate = getattr(wrapper, function_name, None)
        if not callable(candidate):
            raise RuntimeLoadError("The inference wrapper is missing required functions.")
        signature = inspect.signature(candidate)
        positional_parameters = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
        ]
        if len(positional_parameters) < expected_min_args:
            raise RuntimeLoadError("The inference wrapper function signatures are incompatible.")


def _config_project_root(config_path: Path) -> Path:
    if config_path.parent.name == "configs" and len(config_path.parents) >= 2:
        return config_path.parents[1]
    return config_path.parent


def _wrapper_error_code(guarded: dict[str, Any]) -> str | None:
    error = guarded.get("error")
    if isinstance(error, dict) and isinstance(error.get("code"), str):
        return error["code"]
    return None
