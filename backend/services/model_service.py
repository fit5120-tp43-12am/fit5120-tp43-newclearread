# This file calls the ClearRead summary model API to generate summaries and key points
# for each reading block. It also normalises the raw API response into a clean format
# the rest of the app can use.

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
    """Read an environment variable and return it as a boolean."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    """Read an environment variable and return it as an integer, falling back to default."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def is_summary_model_enabled() -> bool:
    """Return True if the summary model is turned on in the environment settings."""
    return _env_bool("CLEARREAD_AI_SUMMARY_ENABLED", True)


def get_summary_max_blocks() -> int:
    """Return the maximum number of blocks that will be sent to the summary model."""
    return max(0, _env_int("CLEARREAD_AI_SUMMARY_MAX_BLOCKS", 100))


def get_summary_max_chars_per_block() -> int:
    """Return the maximum number of characters allowed per block before it is trimmed."""
    return max(1, _env_int("CLEARREAD_AI_SUMMARY_MAX_CHARS_PER_BLOCK", 11000))


def summarize_blocks(texts: list[dict]) -> dict:
    """
    Send a list of text blocks to the ClearRead summary model and return the raw response.

    Args:
        texts (list[dict]): a list of dicts, each with an "id" and "text" field

    Returns:
        dict: the raw JSON response from the summary model API

    Raises:
        RuntimeError: if the requests package is missing, the model is disabled,
                      the API URL or key is not set, or the request fails
    """
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
    """
    Convert the raw summary model response into a simple dict keyed by block ID.

    Args:
        response (dict): the raw JSON response returned by summarize_blocks

    Returns:
        dict: a dict mapping each block ID (str) to its summary result,
              with "status", "summary", and "keyPoints" fields for successes,
              or "status" and "error" fields for failures
    """
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
    """Validate and truncate each text block before sending it to the summary model."""
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
    """Extract key points from a model result item, accepting both camelCase and snake_case keys."""
    raw_key_points = item.get("keyPoints")
    if raw_key_points is None:
        raw_key_points = item.get("key_points")

    if not isinstance(raw_key_points, list):
        return []

    return [str(point).strip() for point in raw_key_points if str(point).strip()]
