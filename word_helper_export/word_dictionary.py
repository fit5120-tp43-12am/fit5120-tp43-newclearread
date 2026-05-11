"""Portable FastAPI feature block for learner-friendly English word breakdown.

This module is designed to be copied into another FastAPI project with minimal
changes. It bundles:
- request / response schemas
- input validation
- a lightweight affix dictionary
- OpenAI Structured Outputs integration
- a ready-to-mount API router
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Literal

from fastapi import APIRouter
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


class WordBreakdownRequest(BaseModel):
    """Request body for analyzing a single English word."""

    word: str = Field(..., description="Single English word to analyze")


MorphemeType = Literal["prefix", "base word", "root", "suffix", "combining form"]


class WordPart(BaseModel):
    """One learner-facing part in the returned word breakdown."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        ...,
        description="Letters as they appear in the word, e.g. mis, interpret, ation.",
    )
    display: str = Field(
        ...,
        description="Learner-friendly label, e.g. mis-, interpret, -ation.",
    )
    type: MorphemeType
    meaning: str = Field(..., description="Short English gloss for this part.")


class WordBreakdownResponse(BaseModel):
    """Structured response returned by the Word Helper endpoint."""

    model_config = ConfigDict(extra="forbid")

    word: str
    can_split: bool
    simple_meaning: str = Field(..., description="Short English meaning of the word.")
    parts: list[WordPart] = Field(default_factory=list)


_ONE_ENGLISH_WORD = re.compile(r"^[A-Za-z]+$")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

PREFIXES: dict[str, str] = {
    "un-": "not / opposite",
    "re-": "again",
    "mis-": "wrongly or badly",
    "dis-": "not / opposite",
}

SUFFIXES: dict[str, str] = {
    "-ness": "the state or quality of something",
    "-able": "able to be",
    "-ly": "in a certain way",
    "-tion": "action, process, or result",
    "-ation": "the action, process, or result of something",
    "-al": "related to",
}

SYSTEM_PROMPT = """Analyze ONE English word for learner-friendly morphology.

Return structured data only.

Rules:
1. Split only when it helps meaning.
2. Never split understand into under + stand.
3. Never split process into pro + cess.
4. Use only English.
5. Keep meanings short and learner-friendly.
6. If the word is best treated as a whole, set can_split=false and return one base word part matching the whole word."""

_openai_client: OpenAI | None = None
_openai_client_key: str | None = None


def _client_for_key(api_key: str) -> OpenAI:
    """Reuse one OpenAI client per API key to avoid repeated setup overhead."""

    global _openai_client, _openai_client_key
    if _openai_client is None or _openai_client_key != api_key:
        _openai_client = OpenAI(api_key=api_key)
        _openai_client_key = api_key
    return _openai_client


def _strip_cjk(text: str) -> str:
    """Remove CJK characters to keep exported learner text English-only."""

    return _CJK_RE.sub("", text).strip()


def _lookup_affix(display_or_label: str) -> str | None:
    """Look up a short fallback gloss for common prefixes and suffixes."""

    part = display_or_label.strip()
    if not part:
        return None
    if part in PREFIXES:
        return PREFIXES[part]
    if part in SUFFIXES:
        return SUFFIXES[part]
    return None


def validate_single_english_word(raw: str) -> tuple[str | None, str | None]:
    """Validate and normalize the incoming word input."""

    word = (raw or "").strip()
    if not word:
        return None, "Please enter one English word."
    if len(word) > 50:
        return None, "Word is too long (maximum 50 letters)."
    if not _ONE_ENGLISH_WORD.fullmatch(word):
        return (
            None,
            "Only one English word is allowed: no spaces, digits, punctuation, or non-English letters.",
        )
    return word, None


def invalid_input_response(original_raw: str, warning: str) -> WordBreakdownResponse:
    """Return a safe, schema-valid response for invalid user input."""

    display = (original_raw or "").strip() or "(empty)"
    return WordBreakdownResponse(
        word=display,
        can_split=False,
        simple_meaning=warning,
        parts=[],
    )


def api_unavailable_response(word: str) -> WordBreakdownResponse:
    """Return a safe fallback when OpenAI is unavailable or parsing fails."""

    return WordBreakdownResponse(
        word=word,
        can_split=False,
        simple_meaning="Word analysis is temporarily unavailable. Please try again later.",
        parts=[],
    )


def _enrich_parts(parts: list[WordPart]) -> list[WordPart]:
    """Fill empty part meanings with lightweight local affix hints when possible."""

    enriched: list[WordPart] = []
    for part in parts:
        meaning = part.meaning
        hint = _lookup_affix(part.display)
        if hint and not meaning.strip():
            meaning = hint
        enriched.append(part.model_copy(update={"meaning": meaning}))
    return enriched


def _sanitize(resp: WordBreakdownResponse) -> WordBreakdownResponse:
    """Clean learner-facing text before sending it back to the caller."""

    return WordBreakdownResponse(
        word=resp.word,
        can_split=resp.can_split,
        simple_meaning=_strip_cjk(resp.simple_meaning),
        parts=[
            WordPart(
                text=part.text,
                display=part.display,
                type=part.type,
                meaning=_strip_cjk(part.meaning),
            )
            for part in resp.parts
        ],
    )


def _finalize_response(
    resp: WordBreakdownResponse, input_word: str
) -> WordBreakdownResponse:
    """Normalize the final model output and apply local post-processing."""

    if resp.word != input_word:
        resp = resp.model_copy(update={"word": input_word})
    resp = resp.model_copy(update={"parts": _enrich_parts(resp.parts)})
    return _sanitize(resp)


def analyze_word_with_openai(word: str) -> WordBreakdownResponse:
    """Call OpenAI Structured Outputs and return a validated response model."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY is not set")
        return api_unavailable_response(word)

    client = _client_for_key(api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "900"))

    try:
        # Native Structured Outputs: the SDK derives a strict schema from the
        # Pydantic model and returns `message.parsed` on success.
        completion = client.beta.chat.completions.parse(
            model=model,
            temperature=0,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"word": word})},
            ],
            response_format=WordBreakdownResponse,
        )
        message = completion.choices[0].message
        refusal = getattr(message, "refusal", None)
        if refusal:
            logger.warning("Structured output refusal: %s", refusal)
            return api_unavailable_response(word)
        if message.parsed is None:
            logger.warning("Structured output returned no parsed payload")
            return api_unavailable_response(word)
        parsed = message.parsed
    except Exception as exc:
        logger.exception("OpenAI structured output failed: %s", exc)
        return api_unavailable_response(word)

    try:
        return _finalize_response(parsed, word)
    except ValidationError:
        logger.warning("Final validation failed")
        return api_unavailable_response(word)


@router.post("/word-breakdown", response_model=WordBreakdownResponse)
def word_breakdown(body: WordBreakdownRequest) -> WordBreakdownResponse:
    """API endpoint for the exported Word Helper feature."""

    normalized, err = validate_single_english_word(body.word)
    if err:
        return invalid_input_response(body.word, err)
    assert normalized is not None
    return analyze_word_with_openai(normalized)
