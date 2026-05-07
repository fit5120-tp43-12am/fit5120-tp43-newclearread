from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .json_utils import parse_json_after_tiny_cleanup


REQUIRED_JUDGE_FIELDS = {
    "parseable_json": bool,
    "schema_ok": bool,
    "main_idea_ok": bool,
    "key_points_ok": bool,
    "simple_english_ok": bool,
    "faithful": bool,
    "missing_critical_info": bool,
    "contains_unsupported_info": bool,
    "high_level_granularity_ok": bool,
    "issue_categories": list,
    "severity": str,
    "retry_focus": list,
    "verdict": str,
    "reason": str,
}

ALLOWED_VERDICTS = {"pass", "retry", "fail"}
ALLOWED_SEVERITIES = {"none", "minor", "major", "critical"}


def parse_and_validate_judge_result(raw_text: str) -> Tuple[Optional[Dict[str, Any]], str, List[str]]:
    parsed, cleaned_text, parse_error = parse_json_after_tiny_cleanup(raw_text)
    if parse_error is not None:
        return None, cleaned_text, [f"invalid_json:{parse_error}"]
    if not isinstance(parsed, dict):
        return None, cleaned_text, ["top_level_not_object"]

    issues: List[str] = []
    keys = set(parsed.keys())
    required = set(REQUIRED_JUDGE_FIELDS.keys())
    missing = sorted(required - keys)
    extra = sorted(keys - required)
    if missing:
        issues.append("missing_fields:" + ",".join(missing))
    if extra:
        issues.append("extra_fields:" + ",".join(extra))

    for field, expected_type in REQUIRED_JUDGE_FIELDS.items():
        if field not in parsed:
            continue
        if not isinstance(parsed[field], expected_type):
            issues.append(f"{field}_wrong_type")

    if isinstance(parsed.get("verdict"), str) and parsed["verdict"] not in ALLOWED_VERDICTS:
        issues.append("invalid_verdict:" + parsed["verdict"])
    if isinstance(parsed.get("severity"), str) and parsed["severity"] not in ALLOWED_SEVERITIES:
        issues.append("invalid_severity:" + parsed["severity"])
    for field in ("issue_categories", "retry_focus"):
        if isinstance(parsed.get(field), list) and not all(isinstance(item, str) for item in parsed[field]):
            issues.append(f"{field}_contains_non_string")

    return (parsed if not issues else None), cleaned_text, issues


def judge_result_is_clean_pass(judge_result: Dict[str, Any]) -> bool:
    return (
        judge_result.get("verdict") == "pass"
        and judge_result.get("parseable_json") is True
        and judge_result.get("schema_ok") is True
        and judge_result.get("main_idea_ok") is True
        and judge_result.get("key_points_ok") is True
        and judge_result.get("simple_english_ok") is True
        and judge_result.get("faithful") is True
        and judge_result.get("missing_critical_info") is False
        and judge_result.get("contains_unsupported_info") is False
        and judge_result.get("high_level_granularity_ok") is True
        and judge_result.get("severity") == "none"
    )
