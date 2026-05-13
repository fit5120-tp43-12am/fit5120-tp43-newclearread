"""Learner-friendly English word breakdown backed by OpenAI Structured Outputs."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError

logger = logging.getLogger(__name__)

MorphemeType = Literal["prefix", "base word", "root", "suffix", "combining form"]
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


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
    """Structured response returned by the word dictionary service."""

    model_config = ConfigDict(extra="forbid")

    word: str
    can_split: bool
    simple_meaning: str = Field(..., description="Short English meaning of the word.")
    parts: list[WordPart] = Field(default_factory=list)

    _source: str = PrivateAttr(default="openai")
    _model: str | None = PrivateAttr(default=None)
    _used_fallback: bool = PrivateAttr(default=False)


_ONE_ENGLISH_WORD = re.compile(r"^[A-Za-z]+(?:['-][A-Za-z]+)*$")
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

    # inflectional endings
    "-ing": "happening now or used as a noun/adjective form",
    "-ed": "past or completed action",
    "-s": "more than one or third-person singular verb form",
    "-es": "more than one or third-person singular verb form",
}

SYSTEM_PROMPT = """Analyze the input only if it is a valid English word or valid English form.

Use short, simple, learner-friendly English.
Return only the required JSON object.
Do not include markdown or extra commentary.

Valid inputs include:
- standard English words
- common contractions, such as "don't"
- possessives, such as "teacher's"
- inflected forms, such as "played", "running", or "books"
- meaningful hyphenated compounds, such as "well-being"
- standard dictionary words that can also be names, such as "shea"

If the input is invalid:
- do not analyze, split, guess, or suggest another word
- set can_split=false
- return parts=[]
- set simple_meaning exactly to:
  The word "<actual input word>" may be incorrect. Please check the spelling and try again.

If the input looks like two or more valid English words joined without a space or hyphen, but the joined form is not a standard word, treat it as invalid.
Example: "previoussingle" is invalid, not "previous" + "single".

Split only when the split clearly helps explain the modern meaning.
Do not force prefix-root-suffix analysis.
Do not split a base word just because it visually contains smaller words.
Do not use old etymological splits if they do not help the modern meaning.
If a split would confuse the learner, treat the word as a whole.

Misleading split examples:
- Do not split "understand" into "under" + "stand".
- Do not split "process" into "pro" + "cess".

If the word is best treated as a whole:
- set can_split=false
- return exactly one part
- the part text must match the whole input
- set the part type to "base word"

For compounds:
- split only into meaningful whole-word parts
- example: "well-being" -> "well" + "being"

For clear learner-useful prefixes or suffixes:
- split them only when they help explain the word
- examples: "unhappy" -> "un" + "happy"; "careless" -> "care" + "less"

For valid -ing forms:
- split into base verb + "-ing" when the base verb is clear
- set can_split=true
- set the "-ing" part type to "suffix"
- restore base spelling when needed
- examples: "playing" -> "play" + "-ing"; "making" -> "make" + "-ing"; "running" -> "run" + "-ing"
- do not split words that only end in the letters "ing" but are not clear -ing forms, such as "king" or "thing"

For contractions, explain the expanded meaning.
For possessives, explain possession or association.
For inflected words, mention the base form only if helpful.

When a base word has multiple meanings, choose the meaning that best matches the whole input word.
Example: in "kidding", "kid" means "to joke or not be serious", not "a child".

Do not mark a word as invalid just because it can also be a personal name.
Analyze it if it is a standard dictionary word or common English form.
Only reject clear personal names that are not standard dictionary words.
Do not suggest spelling corrections.
Do not invent meanings or word parts."""

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
    """Remove CJK characters to keep learner-facing text English-only."""
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


def set_processing_metadata(
    resp: WordBreakdownResponse,
    *,
    source: str,
    model: str | None,
    used_fallback: bool,
) -> WordBreakdownResponse:
    """Attach server-side processing metadata without changing the model schema."""
    resp._source = source
    resp._model = model
    resp._used_fallback = used_fallback
    return resp


def get_processing_metadata(resp: WordBreakdownResponse) -> dict:
    """Return metadata that can be exposed in API responses."""
    return {
        "source": resp._source,
        "model": resp._model,
        "usedFallback": resp._used_fallback,
    }


def _validate_single_english_word(raw: str) -> tuple[str | None, str | None]:
    """Validate and normalize the incoming word input."""
    word = (raw or "").strip()
    if not word:
        return None, "Please enter one English word."
    if len(word) > 50:
        return None, "Word is too long (maximum 50 characters)."
    if not _ONE_ENGLISH_WORD.fullmatch(word):
        return (
            None,
            "Only one English word is allowed: letters may include internal apostrophes or hyphens, but no spaces, digits, or other punctuation.",
        )
    return word, None


def _invalid_input_response(original_raw: str, warning: str) -> WordBreakdownResponse:
    """Return a safe, schema-valid response for invalid user input."""
    display = (original_raw or "").strip() or "(empty)"
    return set_processing_metadata(
        WordBreakdownResponse(
            word=display,
            can_split=False,
            simple_meaning=f'The word "{display}" may be incorrect. Please check the spelling and try again.',
            parts=[],
        ),
        source="invalid_input",
        model=None,
        used_fallback=True,
    )


def _api_unavailable_response(word: str) -> WordBreakdownResponse:
    """Return a safe fallback when OpenAI is unavailable or parsing fails."""
    return set_processing_metadata(
        WordBreakdownResponse(
            word=word,
            can_split=False,
            simple_meaning="Word analysis is temporarily unavailable. Please try again later.",
            parts=[],
        ),
        source="fallback",
        model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        used_fallback=True,
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
    sanitized = WordBreakdownResponse(
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
    return set_processing_metadata(
        sanitized,
        source=resp._source,
        model=resp._model,
        used_fallback=resp._used_fallback,
    )


def _finalize_response(
    resp: WordBreakdownResponse, input_word: str
) -> WordBreakdownResponse:
    """Normalize the final model output and apply local post-processing."""
    if resp.word != input_word:
        resp = resp.model_copy(update={"word": input_word})
    if "{input_word}" in resp.simple_meaning:
        resp = resp.model_copy(
            update={
                "simple_meaning": resp.simple_meaning.replace(
                    "{input_word}", input_word
                )
            }
        )
    resp = resp.model_copy(update={"parts": _enrich_parts(resp.parts)})
    return _sanitize(resp)


def analyze_word_with_openai(word: str) -> WordBreakdownResponse:
    """Call OpenAI Structured Outputs and return a validated response model."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY is not set")
        return _api_unavailable_response(word)

    client = _client_for_key(api_key)
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "900"))

    try:
        response = client.responses.parse(
            model=model,
            max_output_tokens=max_tokens,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"word": word})},
            ],
            text_format=WordBreakdownResponse,
        )
        refusal = getattr(response, "refusal", None)
        if refusal:
            logger.warning("Structured output refusal: %s", refusal)
            return _api_unavailable_response(word)
        if response.output_parsed is None:
            logger.warning("Structured output returned no parsed payload")
            return _api_unavailable_response(word)
        parsed = set_processing_metadata(
            response.output_parsed,
            source="openai",
            model=model,
            used_fallback=False,
        )
    except Exception as exc:
        logger.exception("OpenAI structured output failed: %s", exc)
        return _api_unavailable_response(word)

    try:
        return _finalize_response(parsed, word)
    except ValidationError:
        logger.warning("Final validation failed")
        return _api_unavailable_response(word)


def lookup_word_breakdown(raw: str) -> WordBreakdownResponse:
    """Validate input, then return a safe word breakdown response."""
    normalized, err = _validate_single_english_word(raw)
    if err:
        return _invalid_input_response(raw, err)
    assert normalized is not None
    return analyze_word_with_openai(normalized)
