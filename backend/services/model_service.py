import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import requests
except ImportError:
    requests = None


BACKEND_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(BACKEND_ENV_PATH)

SUMMARY_ENDPOINT = "/v1/clearread/summarize"
DEFAULT_TIMEOUT_SECONDS = 35


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def is_summary_model_enabled() -> bool:
    return _env_bool("CLEARREAD_AI_SUMMARY_ENABLED", True)


def get_summary_max_blocks() -> int:
    return max(0, _env_int("CLEARREAD_AI_SUMMARY_MAX_BLOCKS", 100))


def get_summary_max_chars_per_block() -> int:
    return max(1, _env_int("CLEARREAD_AI_SUMMARY_MAX_CHARS_PER_BLOCK", 11000))


def summarize_blocks(texts: list[dict]) -> dict:
    if requests is None:
        raise RuntimeError("The requests package is required to call the summary model.")
    if not is_summary_model_enabled():
        raise RuntimeError("ClearRead summary model is disabled.")

    api_url = (os.getenv("CLEARREAD_AI_SUMMARY_API_URL") or "").rstrip("/")
    api_key = os.getenv("CLEARREAD_AI_SUMMARY_API_KEY")
    timeout_seconds = _env_int(
        "CLEARREAD_AI_SUMMARY_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS
    )

    if not api_url:
        raise RuntimeError("CLEARREAD_AI_SUMMARY_API_URL is not configured.")
    if not api_key:
        raise RuntimeError("CLEARREAD_AI_SUMMARY_API_KEY is not configured.")

    payload_texts = _prepare_texts(texts)
    if not payload_texts:
        raise RuntimeError("No text blocks were provided for summarization.")

    payload = {
        "requestId": f"reading-{uuid.uuid4()}",
        "texts": payload_texts,
        "options": {"includeDebug": False},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{api_url}{SUMMARY_ENDPOINT}",
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )
    except requests.RequestException as error:
        raise RuntimeError(f"Summary model request failed: {error}") from error

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(
            f"Summary model returned HTTP {response.status_code}: {response.text[:500]}"
        )

    try:
        return response.json()
    except ValueError as error:
        raise RuntimeError("Summary model response was not valid JSON.") from error


def normalize_model_results(response: dict) -> dict:
    if not isinstance(response, dict):
        return {}

    results = response.get("results") or []
    if not isinstance(results, list):
        return {}

    normalized = {}
    for item in results:
        if not isinstance(item, dict):
            continue

        block_id = str(item.get("id") or "").strip()
        if not block_id:
            continue

        status = str(item.get("status") or "").strip().lower()
        if status == "ok":
            normalized[block_id] = {
                "status": "ok",
                "summary": item.get("summary") or "",
                "keyPoints": _normalize_key_points(item),
            }
        else:
            normalized[block_id] = {
                "status": "error",
                "error": item.get("error") or {"message": "Summary model item failed."},
            }

    return normalized


def _prepare_texts(texts: list[dict]) -> list[dict]:
    prepared = []
    max_chars = get_summary_max_chars_per_block()

    for item in texts or []:
        if not isinstance(item, dict):
            continue

        block_id = str(item.get("id") or "").strip()
        block_text = str(item.get("text") or "").strip()
        if not block_id or not block_text:
            continue

        prepared.append(
            {
                "id": block_id,
                "text": block_text[:max_chars].rstrip(),
            }
        )

    return prepared


def _normalize_key_points(item: dict[str, Any]) -> list[str]:
    raw_key_points = item.get("keyPoints")
    if raw_key_points is None:
        raw_key_points = item.get("key_points")

    if not isinstance(raw_key_points, list):
        return []

    return [str(point).strip() for point in raw_key_points if str(point).strip()]
