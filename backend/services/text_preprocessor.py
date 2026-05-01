import json
import os
import re
from typing import Any

try:
    from .text_cleaner import rough_clean_text as cleaner_rough_clean_text
except ImportError:
    from text_cleaner import rough_clean_text as cleaner_rough_clean_text

try:
    import requests
except ImportError:
    requests = None


DEFAULT_CHAT_API_BASE_URL = "https://api.openai.com/v1"
DEFAULT_CHAT_API_MODEL = "gpt-5.4-mini"
CHAT_API_TIMEOUT_SECONDS = 30

CHAT_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_API_BASE_URL = os.getenv("CHAT_API_BASE_URL", DEFAULT_CHAT_API_BASE_URL).rstrip("/")
CHAT_API_MODEL = os.getenv("CHAT_API_MODEL", DEFAULT_CHAT_API_MODEL)

SEGMENT_TYPES = {
    "introduction",
    "background",
    "method",
    "result",
    "discussion",
    "conclusion",
    "general",
    "unknown",
}


def estimate_token_count(text: str) -> int:
    if not text or not text.strip():
        return 0

    word_count = len(re.findall(r"\S+", text))
    return max(1, int(round(word_count * 1.3)))


def rough_clean_text(raw_text: str) -> str:
    return cleaner_rough_clean_text(raw_text)


def split_text_into_sentences(cleaned_text: str) -> list[dict]:
    protected_text = cleaned_text.strip()
    if not protected_text:
        return []

    replacements = {
        "e.g.": "e<PERIOD>g<PERIOD>",
        "i.e.": "i<PERIOD>e<PERIOD>",
        "et al.": "et al<PERIOD>",
        "Fig.": "Fig<PERIOD>",
        "Dr.": "Dr<PERIOD>",
        "Prof.": "Prof<PERIOD>",
        "Mr.": "Mr<PERIOD>",
        "Ms.": "Ms<PERIOD>",
        "Mrs.": "Mrs<PERIOD>",
    }
    for original, replacement in replacements.items():
        protected_text = protected_text.replace(original, replacement)

    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])", protected_text)
    sentences = []
    for part in parts:
        sentence = part.strip()
        if not sentence:
            continue
        for original, replacement in replacements.items():
            sentence = sentence.replace(replacement, original)
        sentences.append({"sentence_id": len(sentences) + 1, "text": sentence})

    return sentences


def build_segmentation_prompt(sentences: list[dict]) -> str:
    numbered_sentences = _build_numbered_sentences(sentences)
    return f"""
You will receive a roughly cleaned document split into numbered sentences.

Your task:
Analyse the semantic structure of the document and group consecutive sentence IDs into meaningful reading segments.

Important rules:
- Preserve the original meaning.
- Do not summarize.
- Do not add new facts.
- Do not copy or rewrite the original text.
- Do not return full segment content.
- Return sentence ID ranges only.
- Keep each segment focused on one topic.
- Each segment should usually contain 600 words after local assembly if possible.
- If the source text is short, fewer words are acceptable.
- Keep conclusion as a separate segment if present.
- Create a short heading for each segment.
- Choose segment_type from: introduction, background, method, result, discussion, conclusion, general, unknown.
- Sentence ranges must be continuous, non-overlapping, and ordered.
- Do not skip any sentence IDs.
- Do not invent sentence IDs.
- Return valid JSON only.
- Do not wrap the JSON in markdown.

Expected JSON:
{{
  "segments": [
    {{
      "segment_id": 1,
      "heading": "Introduction",
      "segment_type": "background",
      "start_sentence_id": 1,
      "end_sentence_id": 8,
      "reason": "This segment introduces the topic and research context."
    }}
  ],
  "processing_notes": [
    "Segmented by semantic boundaries using sentence ID ranges."
  ]
}}

Numbered sentences:
{numbered_sentences}
""".strip()


def call_chat_api(prompt: str) -> dict:
    if requests is None:
        raise RuntimeError("The requests package is required to call the Chat API.")
    if not CHAT_API_KEY:
        raise RuntimeError("CHAT_API_KEY is not configured.")

    url = f"{CHAT_API_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {CHAT_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": CHAT_API_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a text segmentation assistant. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=CHAT_API_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise RuntimeError(f"Chat API request failed: {error}") from error

    if response.status_code != 200:
        raise RuntimeError(
            f"Chat API returned HTTP {response.status_code}: {response.text[:500]}"
        )

    try:
        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"Chat API response format was invalid: {error}") from error

    return _extract_json_object(content)


def assemble_segments_from_sentence_ranges(
    cleaned_text: str,
    sentences: list[dict],
    llm_segments: list,
) -> tuple[list[dict], list[str]]:
    warnings = []
    sentence_count = len(sentences)
    sentence_lookup = {
        sentence["sentence_id"]: sentence["text"] for sentence in sentences
    }
    assembled_segments = []
    expected_start = 1

    for index, segment in enumerate(llm_segments, start=1):
        if not isinstance(segment, dict):
            warnings.append(f"Segment {index} was skipped because it is not an object.")
            continue

        try:
            start_id = int(segment.get("start_sentence_id"))
            end_id = int(segment.get("end_sentence_id"))
        except (TypeError, ValueError):
            warnings.append(f"Segment {index} was skipped because its sentence IDs are invalid.")
            continue

        if start_id < 1 or end_id > sentence_count or start_id > end_id:
            warnings.append(f"Segment {index} was skipped because its sentence range is invalid.")
            continue

        if start_id < expected_start:
            warnings.append(f"Segment {index} overlaps an earlier segment.")
            continue

        if start_id > expected_start:
            warnings.append(
                f"Sentences {expected_start}-{start_id - 1} were not covered by the LLM ranges."
            )

        segment_text = " ".join(
            sentence_lookup[sentence_id]
            for sentence_id in range(start_id, end_id + 1)
            if sentence_id in sentence_lookup
        ).strip()
        if not segment_text:
            warnings.append(f"Segment {index} was skipped because it assembled to empty text.")
            continue

        raw_heading = segment.get("heading")
        heading = str(raw_heading).strip() if raw_heading is not None else None
        if heading == "":
            heading = None
        assembled_segments.append(
            {
                "segment_id": len(assembled_segments) + 1,
                "heading": heading,
                "segment_type": _normalize_segment_type(segment.get("segment_type")),
                "cleaned_text": segment_text,
                "token_count": estimate_token_count(segment_text),
            }
        )
        expected_start = end_id + 1

    if expected_start <= sentence_count:
        warnings.append(
            f"Sentences {expected_start}-{sentence_count} were not covered by the LLM ranges."
        )

    if not assembled_segments:
        warnings.append("No valid sentence ranges remained; used one fallback segment.")
        assembled_segments = [
            {
                "segment_id": 1,
                "heading": None,
                "segment_type": "unknown",
                "cleaned_text": cleaned_text,
                "token_count": estimate_token_count(cleaned_text),
            }
        ]

    return assembled_segments, warnings


def normalize_llm_result(
    api_result: dict,
    model_used: str,
    cleaned_text: str = "",
    sentences: list[dict] | None = None,
) -> dict:
    if not isinstance(api_result, dict):
        raise ValueError("LLM result must be a JSON object.")

    raw_segments = api_result.get("segments")
    if not isinstance(raw_segments, list):
        raw_segments = []

    if not cleaned_text:
        cleaned_text = str(api_result.get("cleaned_text") or "").strip()
    if not cleaned_text:
        raise ValueError("No cleaned_text was available for local segment assembly.")

    sentences = sentences or split_text_into_sentences(cleaned_text)
    segments, validation_warnings = assemble_segments_from_sentence_ranges(
        cleaned_text,
        sentences,
        raw_segments,
    )

    total_token_count = sum(segment["token_count"] for segment in segments)
    processing_notes = _normalize_processing_notes(api_result.get("processing_notes"))

    return {
        "status": "success",
        "segments": segments,
        "metadata": {
            "segment_count": len(segments),
            "total_token_count": total_token_count,
            "model": model_used,
            "processing_notes": processing_notes,
            "segmentation_mode": "sentence_range",
            "validation_warnings": validation_warnings,
        },
    }


def preprocess_text(raw_text: str, debug: bool = False) -> dict:
    rough_cleaned_text = ""
    numbered_sentences: list[dict] = []
    llm_raw_result: dict[str, Any] = {}

    try:
        if raw_text is None:
            return _with_debug(
                _error_response("raw_text is required."),
                debug,
                rough_cleaned_text,
                numbered_sentences,
                llm_raw_result,
            )
        if not isinstance(raw_text, str):
            return _with_debug(
                _error_response("raw_text must be a string."),
                debug,
                rough_cleaned_text,
                numbered_sentences,
                llm_raw_result,
            )
        if not raw_text.strip():
            return _with_debug(
                _error_response("raw_text cannot be empty."),
                debug,
                rough_cleaned_text,
                numbered_sentences,
                llm_raw_result,
            )

        rough_cleaned_text = rough_clean_text(raw_text)
        if not rough_cleaned_text:
            return _with_debug(
                _error_response("No usable text remained after rough cleaning."),
                debug,
                rough_cleaned_text,
                numbered_sentences,
                llm_raw_result,
            )

        numbered_sentences = split_text_into_sentences(rough_cleaned_text)
        if not numbered_sentences:
            return _with_debug(
                _error_response("No usable sentences could be created after rough cleaning."),
                debug,
                rough_cleaned_text,
                numbered_sentences,
                llm_raw_result,
            )

        prompt = build_segmentation_prompt(numbered_sentences)
        llm_raw_result = call_chat_api(prompt)
        result = normalize_llm_result(
            llm_raw_result,
            CHAT_API_MODEL,
            cleaned_text=rough_cleaned_text,
            sentences=numbered_sentences,
        )
        return result
        #return _with_debug(result, debug, rough_cleaned_text, numbered_sentences, llm_raw_result)
        
    except Exception as error:
        return _with_debug(
            _error_response(str(error)),
            debug,
            rough_cleaned_text,
            numbered_sentences,
            llm_raw_result,
        )


def _extract_json_object(content: str) -> dict:
    if not content or not content.strip():
        raise ValueError("Model response was empty.")

    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as original_error:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise ValueError("Model response did not contain a JSON object.") from original_error
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as error:
            raise ValueError(f"Model returned invalid JSON: {error}") from error


def _normalize_segment_type(value: Any) -> str:
    segment_type = str(value or "unknown").strip().lower()
    return segment_type if segment_type in SEGMENT_TYPES else "unknown"


def _normalize_processing_notes(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _build_numbered_sentences(sentences: list[dict]) -> str:
    return "\n".join(
        f"[{sentence['sentence_id']}] {sentence['text']}"
        for sentence in sentences
        if sentence.get("text")
    )


def _error_response(message: str) -> dict:
    return {
        "status": "error",
        "segments": [],
        "metadata": {
            "error": message,
        },
    }


def _with_debug(
    result: dict,
    debug: bool,
    rough_cleaned_text: str,
    numbered_sentences: list[dict],
    llm_raw_result: dict,
) -> dict:
    if debug:
        result["debug"] = {
            "rough_cleaned_text": rough_cleaned_text,
            "numbered_sentences": numbered_sentences,
            "llm_raw_result": llm_raw_result,
        }
    return result
#1

if __name__ == "__main__":
    with open("backend/sample_article.txt", "r", encoding="utf-8") as f:
        sample_text = f.read()

    result = preprocess_text(sample_text, debug=True)
    print(json.dumps(result, indent=2, ensure_ascii=False))
