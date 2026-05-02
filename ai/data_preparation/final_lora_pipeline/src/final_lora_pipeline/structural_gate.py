from __future__ import annotations

from typing import Any, Dict, List

from .json_utils import (
    compact_json,
    force_standard_period,
    normalize_spaces,
    parse_json_after_tiny_cleanup,
    sentence_like_count,
    split_sentence_like_units,
)
from .models import GateResult


REQUIRED_KEYS = ("main_idea", "key_points")


def validate_assistant_label_text(raw_text: str) -> GateResult:
    parsed, cleaned_text, parse_error = parse_json_after_tiny_cleanup(raw_text)
    if parse_error is not None:
        return GateResult(False, None, cleaned_text, [f"invalid_json:{parse_error}"])
    if not isinstance(parsed, dict):
        return GateResult(False, None, cleaned_text, ["top_level_not_object"])
    return validate_assistant_label_object(parsed, cleaned_text)


def validate_assistant_label_object(parsed: Dict[str, Any], cleaned_text: str = "") -> GateResult:
    issues: List[str] = []
    keys = set(parsed.keys())
    required = set(REQUIRED_KEYS)
    if keys != required:
        missing = sorted(required - keys)
        extra = sorted(keys - required)
        if missing:
            issues.append("missing_keys:" + ",".join(missing))
        if extra:
            issues.append("extra_keys:" + ",".join(extra))

    main_idea = parsed.get("main_idea")
    key_points = parsed.get("key_points")
    if not isinstance(main_idea, str):
        issues.append("main_idea_not_string")
    if not isinstance(key_points, list):
        issues.append("key_points_not_array")

    if isinstance(main_idea, str):
        main_units = split_sentence_like_units(main_idea)
        if sentence_like_count(main_idea) != 2:
            issues.append(f"main_idea_sentence_count:{len(main_units)}")
        if any(not unit.strip() for unit in main_units):
            issues.append("main_idea_empty_sentence")

    if isinstance(key_points, list):
        if len(key_points) != 4:
            issues.append(f"key_points_count:{len(key_points)}")
        for index, point in enumerate(key_points):
            if not isinstance(point, str):
                issues.append(f"key_point_{index + 1}_not_string")
                continue
            if not point.strip():
                issues.append(f"key_point_{index + 1}_empty")
                continue
            point_count = sentence_like_count(point)
            if point_count != 1:
                issues.append(f"key_point_{index + 1}_sentence_count:{point_count}")

    return GateResult(not issues, parsed if not issues else None, cleaned_text, issues)


def canonicalize_assistant_label(parsed: Dict[str, Any]) -> Dict[str, Any]:
    main_units = split_sentence_like_units(parsed["main_idea"])
    main_idea = " ".join(force_standard_period(unit) for unit in main_units)
    key_points = [force_standard_period(normalize_spaces(point)) for point in parsed["key_points"]]
    return {
        "main_idea": main_idea,
        "key_points": key_points,
    }


def canonical_assistant_content(parsed: Dict[str, Any]) -> str:
    return compact_json(canonicalize_assistant_label(parsed))
