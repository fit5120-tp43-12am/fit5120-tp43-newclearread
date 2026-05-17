import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class GuardedSummary:
    summary: str
    key_points: list[str]
    action: str


class ResponseGuardError(ValueError):
    pass


def parse_summary(raw_text: str, action: str = "none") -> GuardedSummary:
    data = _loads_json_object(raw_text)

    summary = _clean_text(
        data.get("summary")
        or data.get("main_idea")
        or data.get("mainIdea")
        or data.get("title")
        or ""
    )
    key_points_raw = (
        data.get("keyPoints")
        if data.get("keyPoints") is not None
        else data.get("key_points")
    )

    if not summary:
        raise ResponseGuardError("JSON response is missing summary")
    if not isinstance(key_points_raw, list):
        raise ResponseGuardError("JSON response is missing keyPoints list")

    key_points = [_clean_text(point) for point in key_points_raw]
    key_points = [point for point in key_points if point]
    if not key_points:
        raise ResponseGuardError("JSON response has no usable keyPoints")

    return GuardedSummary(summary=summary, key_points=key_points, action=action)


def _loads_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ResponseGuardError("model output did not contain a JSON object") from None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            raise ResponseGuardError("model output JSON could not be parsed") from error

    if not isinstance(data, dict):
        raise ResponseGuardError("model output JSON must be an object")
    return data


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"\s+", " ", text)
