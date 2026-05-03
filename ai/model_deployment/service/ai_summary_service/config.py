from __future__ import annotations

import os
from dataclasses import dataclass


SERVICE_NAME = "clearread-ai-summary"
API_VERSION = "v1"
DEFAULT_MODEL_LABEL = "clearread-llama31-8b-qlora-candidate-a"
DEFAULT_BASE_MODEL_ID = "unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit"
DEFAULT_MAX_CHARACTERS_PER_TEXT = 11000
DEFAULT_MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024


def _env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return max(value, minimum)


def _env_float(name: str, default: float, minimum: float = 0.1) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        value = float(raw_value)
    except ValueError:
        return default
    return max(value, minimum)


def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class ServiceSettings:
    """Environment-backed configuration for the standalone AI Summary service."""

    api_key: str = ""
    host: str = "127.0.0.1"
    port: int = 8010
    model_label: str = DEFAULT_MODEL_LABEL
    base_model_id: str = DEFAULT_BASE_MODEL_ID
    adapter_dir: str = ""
    inference_config: str = ""
    wrapper_path: str = ""
    max_texts_per_request: int = 32
    max_characters_per_text: int = DEFAULT_MAX_CHARACTERS_PER_TEXT
    max_request_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES
    request_timeout_seconds: float = 120.0
    max_concurrent_requests: int = 1
    enable_debug_responses: bool = False
    runtime: str = "transformers"
    vllm_base_url: str = "http://127.0.0.1:8014"
    vllm_api_key: str = ""
    vllm_model: str = "clearread"
    vllm_internal_concurrency: int = 8
    vllm_request_timeout_seconds: float = 30.0
    vllm_schema_retry_attempts: int = 0
    vllm_max_tokens: int = 320
    service_name: str = SERVICE_NAME
    version: str = API_VERSION

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        return cls(
            api_key=_env_str("CLEARREAD_AI_SERVICE_API_KEY"),
            host=_env_str("CLEARREAD_AI_SERVICE_HOST", "127.0.0.1"),
            port=_env_int("CLEARREAD_AI_SERVICE_PORT", 8010),
            model_label=_env_str("CLEARREAD_AI_MODEL_LABEL", DEFAULT_MODEL_LABEL),
            base_model_id=_env_str("CLEARREAD_AI_BASE_MODEL_ID", DEFAULT_BASE_MODEL_ID),
            adapter_dir=_env_str("CLEARREAD_AI_ADAPTER_DIR"),
            inference_config=_env_str("CLEARREAD_AI_INFERENCE_CONFIG"),
            wrapper_path=_env_str("CLEARREAD_AI_WRAPPER_PATH"),
            max_texts_per_request=_env_int("CLEARREAD_AI_MAX_TEXTS_PER_REQUEST", 32),
            max_characters_per_text=_env_int(
                "CLEARREAD_AI_MAX_CHARACTERS_PER_TEXT",
                DEFAULT_MAX_CHARACTERS_PER_TEXT,
            ),
            max_request_body_bytes=_env_int(
                "CLEARREAD_AI_MAX_REQUEST_BODY_BYTES",
                DEFAULT_MAX_REQUEST_BODY_BYTES,
                minimum=1024,
            ),
            request_timeout_seconds=_env_float("CLEARREAD_AI_REQUEST_TIMEOUT_SECONDS", 120.0),
            max_concurrent_requests=_env_int("CLEARREAD_AI_MAX_CONCURRENT_REQUESTS", 1),
            enable_debug_responses=_env_bool("CLEARREAD_AI_ENABLE_DEBUG_RESPONSES", False),
            runtime=_env_str("CLEARREAD_AI_RUNTIME", "transformers").lower(),
            vllm_base_url=_env_str("CLEARREAD_AI_VLLM_BASE_URL", "http://127.0.0.1:8014"),
            vllm_api_key=_env_str("CLEARREAD_AI_VLLM_API_KEY"),
            vllm_model=_env_str("CLEARREAD_AI_VLLM_MODEL", "clearread"),
            vllm_internal_concurrency=_env_int("CLEARREAD_AI_VLLM_INTERNAL_CONCURRENCY", 8),
            vllm_request_timeout_seconds=_env_float("CLEARREAD_AI_VLLM_REQUEST_TIMEOUT_SECONDS", 30.0),
            vllm_schema_retry_attempts=_env_int("CLEARREAD_AI_VLLM_SCHEMA_RETRY_ATTEMPTS", 0, minimum=0),
            vllm_max_tokens=_env_int("CLEARREAD_AI_VLLM_MAX_TOKENS", 320),
        )

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)
