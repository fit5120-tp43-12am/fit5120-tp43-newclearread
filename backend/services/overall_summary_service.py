# This file generates the overall summary card shown at the top of the reading result page.
# It tries to call OpenAI first. If that fails or is disabled, it falls back to
# pulling a heading and summary text from the first available reading block.

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


BACKEND_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(BACKEND_ENV_PATH)

DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_MAX_CHARS = 50000
DEFAULT_TIMEOUT_SECONDS = 30


class OverallSummaryOutput(BaseModel):
    heading: str
    text: str


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


def generate_overall_summary(text: str, blocks: list[dict] | None = None) -> dict:
    """
    Generate a short overall summary for the full text.
    Tries OpenAI first. If that fails or is turned off, falls back to pulling
    a heading and body from the first available reading block.

    Args:
        text (str): the full source text to summarise
        blocks (list[dict] | None): optional list of pre-processed reading blocks
                                    used by the fallback path

    Returns:
        dict: a dict with "heading" (str) and "text" (str) fields
    """
    source_text = str(text or "").strip()
    block_list = blocks or []

    if not source_text and not block_list:
        return {"heading": "", "text": ""}

    if not _env_bool("CLEARREAD_OVERALL_SUMMARY_ENABLED", True):
        return _fallback_overall_summary(source_text, block_list)

    if not os.getenv("OPENAI_API_KEY"):
        return _fallback_overall_summary(source_text, block_list)

    try:
        return _validate_overall_summary(_call_openai_overall_summary(source_text))
    except Exception:
        return _fallback_overall_summary(source_text, block_list)


def _call_openai_overall_summary(text: str) -> dict:
    """Call the OpenAI API and return a raw overall summary dict with heading and text fields."""
    from openai import OpenAI

    model = os.getenv("CLEARREAD_OVERALL_SUMMARY_MODEL") or DEFAULT_MODEL
    timeout_seconds = _env_int(
        "CLEARREAD_OVERALL_SUMMARY_TIMEOUT_SECONDS",
        DEFAULT_TIMEOUT_SECONDS,
    )
    max_chars = _env_int("CLEARREAD_OVERALL_SUMMARY_MAX_CHARS", DEFAULT_MAX_CHARS)
    clipped_text = text[:max(1, max_chars)].rstrip()

    client = OpenAI(timeout=timeout_seconds)
    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You generate concise reading-support summaries. "
                    "Return only the requested structured output. "
                    "Stay faithful to the source text and do not invent facts."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create an overall summary for the full text.\n\n"
                    "Requirements:\n"
                    "- heading: one short plain-English sentence or phrase, maximum 16 words.\n"
                    "- text: 1 to 3 simple factual sentences summarising the whole text.\n"
                    "- Use accessible wording for readers who may struggle with dense text.\n"
                    "- Do not include markdown, citations, URLs, or bullet points.\n\n"
                    f"Text:\n{clipped_text}"
                ),
            },
        ],
        text_format=OverallSummaryOutput,
    )

    parsed = response.output_parsed
    if isinstance(parsed, OverallSummaryOutput):
        return parsed.model_dump()
    if isinstance(parsed, dict):
        return parsed
    raise ValueError("Overall summary response did not match the expected schema.")


def _validate_overall_summary(summary: dict) -> dict:
    """Clean and validate an overall summary dict, raising ValueError if heading or text is empty."""
    heading = _clean_plain_text(summary.get("heading") if isinstance(summary, dict) else "")
    text = _clean_plain_text(summary.get("text") if isinstance(summary, dict) else "")

    if not heading or not text:
        raise ValueError("Overall summary is missing heading or text.")

    return {
        "heading": _limit_words(heading, 18),
        "text": _limit_sentences(_limit_words(text, 90), 3),
    }


def _fallback_overall_summary(text: str, blocks: list[dict]) -> dict:
    """Build an overall summary from block metadata or raw text when OpenAI is unavailable."""
    heading = ""
    body = ""

    for block in blocks:
        if not isinstance(block, dict):
            continue
        heading = heading or _clean_plain_text(block.get("title") or "")
        body = body or _clean_plain_text(block.get("summary") or block.get("subtitle") or "")
        if heading and body:
            break

    if not heading:
        heading = _pick_fallback_heading(text)
    if not body:
        body = _pick_fallback_body(text, blocks)

    return {
        "heading": heading,
        "text": body,
    }


def _pick_fallback_heading(text: str) -> str:
    """Return a short heading derived from the first sentence of the text, or a default label."""
    first_sentence = _first_sentence(text)
    if first_sentence:
        return _limit_words(first_sentence, 16)
    return "Summary"


def _pick_fallback_body(text: str, blocks: list[dict]) -> str:
    """Build fallback body text from block summaries or the first sentence of raw text."""
    block_summaries = [
        _clean_plain_text(block.get("summary") or block.get("subtitle") or "")
        for block in blocks
        if isinstance(block, dict)
    ]
    joined = " ".join(summary for summary in block_summaries[:3] if summary)
    if joined:
        return _limit_sentences(_limit_words(joined, 80), 3)

    fallback_sentence = _first_sentence(text)
    if fallback_sentence:
        return _limit_sentences(_limit_words(fallback_sentence, 80), 2)
    return ""


def _first_sentence(text: str) -> str:
    """Return the first sentence of a cleaned text string."""
    cleaned = _clean_plain_text(text)
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return parts[0].strip() if parts else cleaned[:220].strip()


def _clean_plain_text(value: object) -> str:
    """Strip URLs, markdown symbols, and extra whitespace from a value, returning plain text."""
    text = str(value or "")
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"[*_`>#\[\]]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text


def _limit_words(text: str, max_words: int) -> str:
    """Trim text to at most max_words words, ending with a period if truncated."""
    words = text.split()
    if len(words) <= max_words:
        return text
    clipped = " ".join(words[:max_words]).rstrip(" ,;:")
    if clipped and clipped[-1] not in ".!?":
        clipped += "."
    return clipped


def _limit_sentences(text: str, max_sentences: int) -> str:
    """Return at most max_sentences sentences from the text."""
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if not parts:
        return text.strip()
    return " ".join(parts[:max(1, max_sentences)]).strip()
