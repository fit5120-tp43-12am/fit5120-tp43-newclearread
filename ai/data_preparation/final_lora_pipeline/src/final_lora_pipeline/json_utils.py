from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple


_FENCE_RE = re.compile(r"^```(?:json|JSON)?\s*(.*?)\s*```$", re.DOTALL)
_LABEL_RE = re.compile(r"^(?:json|JSON)\s*:?\s*(\{.*\})\s*$", re.DOTALL)


def tiny_cleanup_json_text(text: str) -> str:
    cleaned = text.strip()
    fence_match = _FENCE_RE.match(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    label_match = _LABEL_RE.match(cleaned)
    if label_match:
        cleaned = label_match.group(1).strip()
    return cleaned


def parse_json_after_tiny_cleanup(text: str) -> Tuple[Optional[Any], str, Optional[str]]:
    cleaned = tiny_cleanup_json_text(text)
    try:
        return json.loads(cleaned), cleaned, None
    except json.JSONDecodeError as exc:
        return None, cleaned, str(exc)


def compact_json(value: Dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


_ABBREVIATIONS = {
    "a.m",
    "c",
    "e.g",
    "i.e",
    "etc",
    "mr",
    "mrs",
    "ms",
    "dr",
    "prof",
    "fig",
    "vs",
    "u.s",
    "u.k",
    "no",
    "p.m",
    "st",
}

_NON_BOUNDARY_AFTER_DOTTED_ABBREVIATION = {
    "agency",
    "agencies",
    "business",
    "businesses",
    "citizen",
    "citizens",
    "company",
    "companies",
    "department",
    "departments",
    "embassy",
    "embassies",
    "government",
    "governments",
    "law",
    "laws",
    "resident",
    "residents",
    "state",
    "states",
    "territories",
    "territory",
    "visa",
    "visas",
    "worker",
    "workers",
}

_WEB_SUFFIXES = {"com", "edu", "gov", "mil", "net", "org"}


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _looks_like_abbreviation(chunk: str) -> bool:
    match = re.search(r"([A-Za-z](?:[A-Za-z.]*[A-Za-z])?)\.$", chunk.strip())
    if not match:
        return False
    token = match.group(1).lower()
    return token in _ABBREVIATIONS


def _abbreviation_token(chunk: str) -> Optional[str]:
    match = re.search(r"([A-Za-z](?:[A-Za-z.]*[A-Za-z])?)\.$", chunk.strip())
    if not match:
        return None
    token = match.group(1).lower()
    return token if token in _ABBREVIATIONS else None


def _is_internal_dotted_abbreviation_period(text: str, index: int) -> bool:
    return (
        index > 0
        and index + 1 < len(text)
        and text[index - 1].isalpha()
        and text[index + 1].isalpha()
        and index + 2 < len(text)
        and text[index + 2] == "."
    )


def _is_domain_like_period(text: str, index: int) -> bool:
    if index + 1 >= len(text) or not text[index + 1].isalpha():
        return False
    prev_char = text[index - 1] if index > 0 else ""
    if prev_char.isalnum():
        return True
    suffix = text[index + 1 : index + 4].lower()
    after_suffix = text[index + 4] if index + 4 < len(text) else ""
    return suffix in _WEB_SUFFIXES and not after_suffix.isalpha()


def _next_word(text: str, index: int) -> str:
    match = re.search(r"\s+([A-Za-z][A-Za-z-]*)", text[index + 1 :])
    return match.group(1) if match else ""


def _abbreviation_period_is_sentence_boundary(text: str, index: int, token: str) -> bool:
    next_word = _next_word(text, index)
    if not next_word:
        return False
    if token in {"e.g", "i.e", "a.m", "p.m"}:
        return False
    if token == "c" and next_word[:1].islower():
        return False
    if "." in token:
        if next_word[:1].islower():
            return False
        if next_word.isupper() and len(next_word) <= 6:
            return False
        if next_word.lower() in _NON_BOUNDARY_AFTER_DOTTED_ABBREVIATION:
            return False
        return True
    if token in {"mr", "mrs", "ms", "dr", "prof", "fig", "vs", "no", "st"}:
        return False
    return next_word[:1].isupper()


def split_sentence_like_units(text: str) -> List[str]:
    normalized = normalize_spaces(text)
    if not normalized:
        return []

    units: List[str] = []
    start = 0
    i = 0
    while i < len(normalized):
        char = normalized[i]
        if char in ".!?":
            prev_char = normalized[i - 1] if i > 0 else ""
            next_char = normalized[i + 1] if i + 1 < len(normalized) else ""
            if char == "." and prev_char.isdigit() and next_char.isdigit():
                i += 1
                continue
            if char == "." and _is_internal_dotted_abbreviation_period(normalized, i):
                i += 1
                continue
            if char == "." and _is_domain_like_period(normalized, i):
                i += 1
                continue
            chunk = normalized[start : i + 1]
            if char == ".":
                token = _abbreviation_token(chunk)
                if token is not None and not _abbreviation_period_is_sentence_boundary(normalized, i, token):
                    i += 1
                    continue
            units.append(chunk.strip())
            start = i + 1
        i += 1

    tail = normalized[start:].strip()
    if tail:
        units.append(tail)
    return [unit for unit in units if unit]


def sentence_like_count(text: str) -> int:
    return len(split_sentence_like_units(text))


def force_standard_period(text: str) -> str:
    normalized = normalize_spaces(text)
    if not normalized:
        return normalized
    while normalized.endswith(".."):
        normalized = normalized[:-1].rstrip()
    if normalized.endswith((".", "!", "?")):
        normalized = normalized[:-1].rstrip()
    return f"{normalized}."
