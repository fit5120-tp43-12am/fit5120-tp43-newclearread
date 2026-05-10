import asyncio
import json
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from typing import Any

from pydantic import BaseModel, Field


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_BATCH_SIZE = 96


class SegmentCardOutput(BaseModel):
    viewpoint: str = Field(
        max_length=36,
        description="A compact 3-7 word section card title.",
    )
    summary: str = Field(
        max_length=90,
        description="A concise one-sentence section card preview.",
    )


class SegmentCardItem(SegmentCardOutput):
    segment_id: int


class SegmentCardBatchOutput(BaseModel):
    items: list[SegmentCardItem]

SEGMENT_TYPES = {
    "introduction",
    "background",
    "method",
    "result",
    "discussion",
    "conclusion",
    "general",
    "unknown",
    "mental health",
}

WEAK_VIEWPOINTS = {
    "background",
    "discussion",
    "method",
    "result",
    "general",
    "unknown",
}

ABBREVIATIONS = {
    "e.g.",
    "i.e.",
    "dr.",
    "mr.",
    "mrs.",
    "ms.",
    "prof.",
    "fig.",
    "etc.",
    "vs.",
    "al.",
}

REFERENCE_HEADINGS = {
    "references",
    "bibliography",
    "works cited",
}

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "as",
    "by",
    "from",
    "this",
    "that",
    "these",
    "those",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "it",
    "its",
    "at",
    "we",
    "they",
    "their",
    "have",
    "has",
    "had",
    "not",
    "can",
    "may",
    "will",
    "which",
    "such",
}


def clean_text(text: str) -> str:
    if text is None:
        return ""

    text = str(text).strip()
    replacements = {
        "\r\n": "\n",
        "\r": "\n",
        "\u00a0": " ",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    paragraphs = []
    current = []

    for line in lines:
        if not line:
            _flush_paragraph(paragraphs, current)
            current = []
            continue

        if _is_markdown_heading(line) or _is_reference_heading(line):
            _flush_paragraph(paragraphs, current)
            current = []
            paragraphs.append(line)
            continue

        current.append(line)

    _flush_paragraph(paragraphs, current)
    cleaned = "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ""))


def split_into_sentences(text: str) -> list[dict]:
    cleaned = clean_text(text)
    if not cleaned:
        return []

    sentences = []
    in_references = False

    for paragraph in cleaned.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        heading_level = _heading_level(paragraph)
        is_heading = heading_level is not None or _is_reference_heading(paragraph)

        if _is_reference_heading(paragraph):
            in_references = True

        if is_heading:
            sentences.append(
                _make_sentence(
                    len(sentences) + 1,
                    paragraph,
                    heading_level=heading_level,
                    is_heading=True,
                    is_reference=in_references,
                )
            )
            continue

        protected = _protect_abbreviations(paragraph)
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])", protected)

        for part in parts:
            sentence = _restore_abbreviations(part).strip()
            if sentence:
                sentences.append(
                    _make_sentence(
                        len(sentences) + 1,
                        sentence,
                        heading_level=None,
                        is_heading=False,
                        is_reference=in_references or _looks_like_reference_line(sentence),
                    )
                )

    return sentences


def build_sentence_blocks(sentences: list[dict], block_size: int = 4) -> list[dict]:
    if block_size < 3:
        block_size = 3
    if block_size > 5:
        block_size = 5

    blocks = []
    for index in range(0, len(sentences), block_size):
        block_sentences = sentences[index : index + block_size]
        if not block_sentences:
            continue

        text = " ".join(sentence["text"] for sentence in block_sentences).strip()
        blocks.append(
            {
                "block_id": len(blocks) + 1,
                "start_sentence_id": block_sentences[0]["sentence_id"],
                "end_sentence_id": block_sentences[-1]["sentence_id"],
                "text": text,
                "word_count": count_words(text),
            }
        )

    return blocks


def embed_texts_openai(
    texts: list[str],
    model: str = DEFAULT_EMBEDDING_MODEL,
    dimensions: int | None = None,
) -> list[list[float]]:
    if not texts:
        raise ValueError("texts must not be empty.")

    cleaned_texts = [str(text).strip() for text in texts]
    if any(not text for text in cleaned_texts):
        raise ValueError("texts must not contain empty strings.")

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not configured.")

    try:
        from openai import OpenAI
    except ImportError as error:
        raise ImportError("The openai package is required for embedding detection.") from error

    client = OpenAI()
    embeddings: list[list[float]] = []

    for start in range(0, len(cleaned_texts), EMBEDDING_BATCH_SIZE):
        batch = cleaned_texts[start : start + EMBEDDING_BATCH_SIZE]
        request_body: dict[str, Any] = {
            "model": model,
            "input": batch,
        }
        if dimensions is not None:
            request_body["dimensions"] = dimensions

        try:
            response = client.embeddings.create(**request_body)
        except Exception as error:
            raise RuntimeError(f"OpenAI embedding request failed: {error}") from error

        batch_embeddings = [item.embedding for item in response.data]
        if len(batch_embeddings) != len(batch):
            raise RuntimeError("OpenAI embedding response length did not match input length.")
        embeddings.extend(batch_embeddings)

    return embeddings


def cosine_similarity_vector(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0

    dot_product = sum(left * right for left, right in zip(a, b))
    magnitude_a = math.sqrt(sum(value * value for value in a))
    magnitude_b = math.sqrt(sum(value * value for value in b))

    if not magnitude_a or not magnitude_b:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def detect_boundaries_with_embeddings(
    blocks: list[dict],
    embeddings: list[list[float]],
) -> list[dict]:
    if len(blocks) < 2:
        return []
    if len(blocks) != len(embeddings):
        raise ValueError("Number of embeddings must match number of blocks.")

    boundaries = []
    for index in range(len(blocks) - 1):
        similarity = cosine_similarity_vector(embeddings[index], embeddings[index + 1])
        boundaries.append(
            {
                "after_sentence_id": blocks[index]["end_sentence_id"],
                "before_block_id": blocks[index]["block_id"],
                "after_block_id": blocks[index + 1]["block_id"],
                "similarity": round(similarity, 6),
                "boundary_strength": round(1 - similarity, 6),
                "source": "embedding",
            }
        )

    return sorted(boundaries, key=lambda item: item["boundary_strength"], reverse=True)


def detect_boundaries_tfidf(blocks: list[dict]) -> list[dict]:
    if len(blocks) < 2:
        return []

    vectors = _build_tfidf_vectors([block["text"] for block in blocks])
    boundaries = []

    for index in range(len(blocks) - 1):
        similarity = _cosine_similarity_sparse(vectors[index], vectors[index + 1])
        boundaries.append(
            {
                "after_sentence_id": blocks[index]["end_sentence_id"],
                "before_block_id": blocks[index]["block_id"],
                "after_block_id": blocks[index + 1]["block_id"],
                "similarity": round(similarity, 6),
                "boundary_strength": round(1 - similarity, 6),
                "source": "tfidf_fallback",
            }
        )

    return sorted(boundaries, key=lambda item: item["boundary_strength"], reverse=True)


def assemble_segments(
    sentences: list[dict],
    boundaries: list[dict],
    target_words: int = 650,
    min_words: int = 450,
    max_words: int = 850,
) -> list[dict]:
    if not sentences:
        return []

    total_words = sum(sentence["word_count"] for sentence in sentences)
    if total_words <= max_words:
        return _split_segments_with_many_major_headings(
            [_make_raw_segment_from_slice(sentences, 0, len(sentences) - 1)],
            min_words,
        )

    boundary_by_after_id = _merge_boundaries_by_sentence_id(
        boundaries + _heading_boundaries(sentences)
    )
    raw_segments = []
    current_start_index = 0

    while current_start_index < len(sentences):
        end_index = _select_segment_end_index(
            sentences,
            current_start_index,
            boundary_by_after_id,
            target_words,
            min_words,
            max_words,
        )
        raw_segments.append(
            _make_raw_segment_from_slice(sentences, current_start_index, end_index)
        )
        current_start_index = end_index + 1

    raw_segments = _split_segments_with_many_major_headings(raw_segments, min_words)
    return _merge_short_final_segment(raw_segments, min_words, max_words)


def classify_segment_type(content: str, segment_index: int, total_segments: int) -> str:
    text = content.lower()
    headings = [_normalize_heading_text(match) for match in re.findall(r"(?m)^#{1,6}\s+(.+)$", content)]

    if any(heading in {"conclusion", "final thoughts", "summary"} for heading in headings):
        return "conclusion"
    if total_segments > 1 and segment_index == total_segments and re.search(
        r"\b(in conclusion|to conclude|overall|the most important point)\b",
        text,
    ):
        return "conclusion"

    if segment_index == 1 and (
        any(heading in {"introduction", "overview", "purpose"} for heading in headings)
        or re.search(r"\b(this essay|this article|this paper|main argument|introduces)\b", text)
    ):
        return "introduction"

    if _has_strong_method_evidence(text, headings):
        return "method"
    if _has_strong_result_evidence(text, headings):
        return "result"

    if re.search(
        r"\b(definition|defined|means|causes|context|background|prior|previous|related work|why it matters|theory)\b",
        text,
    ):
        return "background"

    if re.search(
        r"\b(challenge|challenges|implication|implications|solution|solutions|should|could|however|therefore|trade-off|stigma|inequality|pressure|burnout)\b",
        text,
    ):
        return "discussion"

    return "general"


def summarize_segment(content: str, source_sentences: list[dict] | None = None) -> str:
    if not content or not str(content).strip():
        return ""

    prompt = f"""
You will receive one text segment.

Task:
Write one concise summary sentence for this segment.

Rules:
- Summarize the whole segment, not only the first or last part.
- Do not copy a full sentence directly from the segment.
- Do not add information not present in the segment.
- Preserve the main causal, argumentative, or explanatory relationship.
- If the segment contains multiple topics, connect them clearly.
- Ignore references, citation markers, metadata, table labels, figure labels, copyright text, DOI text, and affiliation text.
- Return valid JSON only.
- Do not wrap the JSON in markdown.

Expected JSON:
{{
  "summary": "One concise summary sentence."
}}

Segment:
{content}
""".strip()

    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is not configured.")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise ImportError("The openai package is required for LLM summaries.") from error

        client = OpenAI()
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4.1-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "You return strict JSON for one segment summary.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            timeout=30,
        )
        raw_content = response.choices[0].message.content or ""

        try:
            data = _extract_json_object(raw_content)
            summary = str(data.get("summary") or "").strip()
        except Exception:
            match = re.search(r'"summary"\s*:\s*"([^"]+)"', raw_content, flags=re.DOTALL)
            summary = match.group(1).strip() if match else raw_content.strip()

        summary = _clean_sentence_for_output(_trim_summary(summary, 45))
        lowered = summary.lower()
        if not summary or count_words(summary) < 8 or count_words(summary) > 70:
            raise ValueError("LLM summary failed validation.")
        if "```" in summary or re.match(r"^this segment discusses\b", lowered):
            raise ValueError("LLM summary used a weak or invalid format.")
        if "http://" in lowered or "https://" in lowered or "www." in lowered:
            raise ValueError("LLM summary contains a URL.")
        return summary
    except Exception:
        return _summarize_segment_local(content, source_sentences)


def _summarize_segment_local(content: str, source_sentences: list[dict] | None = None) -> str:
    sentences = source_sentences or split_into_sentences(content)
    content_sentences = [
        sentence
        for sentence in sentences
        if not sentence.get("is_heading") and not sentence.get("is_reference")
    ]
    if not content_sentences:
        return ""

    candidates = [sentence for sentence in content_sentences if _is_summary_candidate(sentence)]
    if not candidates:
        candidates = content_sentences
    if not candidates:
        return ""

    def is_metadata_like(text: str) -> bool:
        lowered = text.lower()
        return bool(
            re.search(
                r"\b(doi|copyright|all rights reserved|correspondence|affiliation|"
                r"university|journal|figure|fig\.|table|references|bibliography)\b",
                lowered,
            )
            or "http://" in lowered
            or "https://" in lowered
            or "www." in lowered
        )

    def position_bonus(relative_position: float) -> float:
        early = max(0.0, 0.28 - relative_position * 0.45)
        middle = max(0.0, 0.18 - abs(relative_position - 0.5) * 0.36)
        late = max(0.0, 0.16 - abs(relative_position - 0.85) * 0.32)
        return early + middle + late

    important_terms = Counter(
        token for token in _tokenize(content) if token not in STOPWORDS and len(token) > 2
    )
    heading_sentences = [
        sentence
        for sentence in sentences
        if sentence.get("is_heading") and not sentence.get("is_reference")
    ]
    heading_terms = {
        token
        for sentence in heading_sentences
        for token in _tokenize(sentence["text"])
        if token not in STOPWORDS and len(token) > 2
    }

    sentence_positions = {
        id(sentence): index for index, sentence in enumerate(content_sentences)
    }
    scored_candidates = []
    denominator = max(len(content_sentences) - 1, 1)

    for sentence in candidates:
        text = sentence["text"]
        tokens = [token for token in _tokenize(text) if token not in STOPWORDS]
        if not tokens:
            continue

        sentence_word_count = count_words(text)
        relative_position = sentence_positions.get(id(sentence), 0) / denominator
        lowered = text.lower()

        score = sum(important_terms[token] for token in tokens) / max(len(tokens), 1)
        score += len(set(tokens) & heading_terms) * 0.35
        score += position_bonus(relative_position)

        if 12 <= sentence_word_count <= 45:
            score += 0.35
        elif sentence_word_count < 8:
            score -= 0.7
        elif sentence_word_count > 70:
            score -= 0.55

        if re.search(
            r"\b(this means|therefore|the main|the key|important|suggests|shows|"
            r"indicates|requires|depends|because|however|overall|in conclusion)\b",
            lowered,
        ):
            score += 0.45

        score -= _citation_count(text) * 0.25
        if re.match(r"^(for example|for instance|in some cases)\b", lowered):
            score -= 0.45
        if is_metadata_like(text):
            score -= 1.0

        scored_candidates.append(
            {
                "sentence": sentence,
                "score": score,
                "position": sentence_positions.get(id(sentence), 0),
            }
        )

    if not scored_candidates:
        return ""

    max_sentences = 3 if len(heading_sentences) > 1 or count_words(content) > 650 else 2
    max_sentences = min(max_sentences, len(scored_candidates))
    selected = []

    for candidate in sorted(scored_candidates, key=lambda item: item["score"], reverse=True):
        if len(selected) >= max_sentences:
            break
        if any(abs(candidate["position"] - item["position"]) <= 1 for item in selected):
            continue
        selected.append(candidate)

    if len(selected) < max_sentences:
        for candidate in sorted(scored_candidates, key=lambda item: item["score"], reverse=True):
            if len(selected) >= max_sentences:
                break
            if candidate not in selected:
                selected.append(candidate)

    selected = sorted(selected, key=lambda item: item["position"])
    joined_summary = " ".join(item["sentence"]["text"].strip() for item in selected)
    max_summary_words = 75 if len(selected) > 1 else 40
    return _clean_sentence_for_output(_trim_summary(joined_summary, max_summary_words))


def generate_viewpoint(content: str, source_sentences: list[dict] | None = None) -> str:
    sentences = source_sentences or split_into_sentences(content)
    headings = [
        _normalize_heading_text(sentence["text"])
        for sentence in sentences
        if sentence.get("is_heading") and not sentence.get("is_reference")
    ]
    candidates = [sentence for sentence in sentences if _is_summary_candidate(sentence)]
    summary = _summarize_segment_local(content, sentences)

    viewpoint_candidates = []
    role_viewpoint = _construct_role_viewpoint(content, headings, summary)
    if role_viewpoint:
        viewpoint_candidates.append(role_viewpoint)
    if summary:
        viewpoint_candidates.append(summary)
    for heading in headings:
        if heading and heading not in WEAK_VIEWPOINTS and heading not in REFERENCE_HEADINGS:
            viewpoint_candidates.append(heading)
    for sentence in candidates[:3]:
        viewpoint_candidates.append(sentence["text"])

    for candidate in viewpoint_candidates:
        viewpoint = _clean_viewpoint(candidate)
        if _is_valid_viewpoint_text(viewpoint, allow_short=True):
            return viewpoint

    important_terms = [
        term
        for term, _ in Counter(
            token for token in _tokenize(content) if token not in STOPWORDS and len(token) > 3
        ).most_common(4)
    ]
    if important_terms:
        return _clean_viewpoint(" ".join(important_terms).capitalize() + " shape the central issue.")

    return "This segment presents one main idea."


def validate_segments(segments: list[dict], cleaned_text: str) -> None:
    validate_segments_detailed(segments, cleaned_text, split_into_sentences(cleaned_text))


def validate_segments_detailed(
    segments: list[dict],
    cleaned_text: str,
    sentences: list[dict],
    keep_references: bool = False,
) -> None:
    if not isinstance(segments, list):
        raise ValueError("Segments must be a list.")

    expected_sentence_ids = [
        sentence["sentence_id"]
        for sentence in sentences
        if keep_references or not sentence.get("is_reference")
    ]
    assigned_sentence_ids = []
    seen_content = set()
    seen_long_sentences: dict[str, int] = {}
    total_segment_words = 0
    previous_end_id = 0

    for expected_segment_id, segment in enumerate(segments, start=1):
        if segment.get("segment_id") != expected_segment_id:
            raise ValueError("Segment IDs must be continuous and start from 1.")
        _validate_viewpoint(segment.get("viewpoint", ""), expected_segment_id)
        _validate_summary(segment.get("summary", ""), expected_segment_id)
        if not segment.get("content", "").strip():
            raise ValueError("Segment content must not be empty.")
        if segment.get("word_count") != count_words(segment["content"]):
            raise ValueError("Segment word_count does not match segment content.")

        sentence_ids = segment.get("sentence_ids")
        if not sentence_ids:
            raise ValueError(f"Segment {expected_segment_id} has no sentence_ids.")
        if sentence_ids != sorted(sentence_ids):
            raise ValueError(f"Segment {expected_segment_id} sentence_ids are not strictly increasing.")
        if len(sentence_ids) != len(set(sentence_ids)):
            raise ValueError(f"Segment {expected_segment_id} contains duplicated sentence_ids.")
        if sentence_ids[0] <= previous_end_id:
            raise ValueError("Segment ranges are not strictly increasing.")
        previous_end_id = sentence_ids[-1]

        if not keep_references and any(_sentence_by_id(sentences, sentence_id).get("is_reference") for sentence_id in sentence_ids):
            raise ValueError("References were included while keep_references is False.")

        content_key = _normalize_for_duplicate_check(segment["content"])
        if content_key in seen_content:
            raise ValueError("Duplicated segment content detected.")
        seen_content.add(content_key)

        _validate_repeated_shingles(segment["content"], expected_segment_id)
        for sentence_id in sentence_ids:
            sentence = _sentence_by_id(sentences, sentence_id)
            normalized_sentence = _normalize_for_duplicate_check(sentence["text"])
            if sentence["word_count"] >= 10 and normalized_sentence in seen_long_sentences:
                raise ValueError("The same long sentence appears in multiple segments.")
            if sentence["word_count"] >= 10:
                seen_long_sentences[normalized_sentence] = expected_segment_id

        assigned_sentence_ids.extend(sentence_ids)
        total_segment_words += segment["word_count"]

    duplicated_ids = sorted(
        sentence_id for sentence_id, count in Counter(assigned_sentence_ids).items() if count > 1
    )
    if duplicated_ids:
        raise ValueError(f"Duplicated sentence_id values detected: {duplicated_ids[:10]}.")

    missing_ids = sorted(set(expected_sentence_ids) - set(assigned_sentence_ids))
    if missing_ids:
        raise ValueError(f"Missing sentence_id values detected: {missing_ids[:10]}.")

    unexpected_ids = sorted(set(assigned_sentence_ids) - set(expected_sentence_ids))
    if unexpected_ids:
        raise ValueError(f"Unexpected sentence_id values detected: {unexpected_ids[:10]}.")

    if assigned_sentence_ids != sorted(assigned_sentence_ids):
        raise ValueError("Final segment sentence order does not follow the source order.")

    expected_word_count = sum(
        sentence["word_count"]
        for sentence in sentences
        if keep_references or not sentence.get("is_reference")
    )
    allowed_difference = max(3, int(expected_word_count * 0.05))
    if abs(total_segment_words - expected_word_count) > allowed_difference:
        raise ValueError("Segment word count does not match non-reference cleaned input word count.")


def preprocess_text(
    text: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
    target_words: int = 650,
    min_words: int = 450,
    max_words: int = 850,
    block_size: int = 4,
    fallback_to_tfidf: bool = True,
    keep_references: bool = False,
    debug: bool = False,
    enrich_with_llm: bool = True,
    llm_model: str = "gpt-4.1-mini",
    llm_concurrency: int = 5,
    llm_max_retries: int = 1,
) -> dict:
    cleaned = clean_text(text)
    if not cleaned:
        return {"segments": [], "debug": _empty_debug() } if debug else {"segments": []}

    all_sentences = split_into_sentences(cleaned)
    content_sentences = [
        sentence for sentence in all_sentences if keep_references or not sentence.get("is_reference")
    ]
    if not content_sentences:
        return {"segments": [], "debug": _empty_debug(all_sentences)} if debug else {"segments": []}

    blocks = build_sentence_blocks(content_sentences, block_size=block_size)
    boundaries = []
    if len(blocks) >= 2:
        try:
            embeddings = embed_texts_openai([block["text"] for block in blocks], model=model)
            boundaries = detect_boundaries_with_embeddings(blocks, embeddings)
        except Exception:
            if not fallback_to_tfidf:
                raise
            boundaries = detect_boundaries_tfidf(blocks)

    raw_segments = assemble_segments(
        content_sentences,
        boundaries,
        target_words=target_words,
        min_words=min_words,
        max_words=max_words,
    )

    total_segments = len(raw_segments)
    internal_segments = []
    for index, raw_segment in enumerate(raw_segments, start=1):
        content = raw_segment["content"].strip()
        summary = _summarize_segment_local(content, raw_segment["_sentences"])
        internal_segments.append(
            {
                "segment_id": index,
                "viewpoint": generate_viewpoint(content, raw_segment["_sentences"]),
                "summary": summary,
                "word_count": count_words(content),
                "content": content,
                "start_sentence_id": raw_segment["start_sentence_id"],
                "end_sentence_id": raw_segment["end_sentence_id"],
                "sentence_ids": raw_segment["sentence_ids"],
                "_sentences": raw_segment["_sentences"],
                "split_reason": raw_segment.get("split_reason", "semantic_or_size_boundary"),
            }
        )

    validate_segments_detailed(
        internal_segments,
        cleaned,
        all_sentences,
        keep_references=keep_references,
    )

    public_segments = [_public_segment(segment) for segment in internal_segments]
    if enrich_with_llm:
        public_segments = _run_async_enrichment_sync(
            public_segments,
            model=llm_model,
            concurrency=llm_concurrency,
            max_retries=llm_max_retries,
        )

    result = {"segments": public_segments}
    if debug:
        result["debug"] = {
            "sentence_count": len(all_sentences),
            "content_sentence_count": len(content_sentences),
            "reference_sentence_count": len(all_sentences) - len(content_sentences),
            "boundaries": boundaries + _heading_boundaries(content_sentences),
            "segment_sentence_ranges": [
                {
                    "segment_id": segment["segment_id"],
                    "start_sentence_id": segment["start_sentence_id"],
                    "end_sentence_id": segment["end_sentence_id"],
                    "sentence_ids": segment["sentence_ids"],
                }
                for segment in internal_segments
            ],
            "segment_viewpoints": [
                segment["viewpoint"] for segment in public_segments
            ],
            "heading_count_per_segment": [
                len([sentence for sentence in segment["_sentences"] if sentence.get("is_heading")])
                for segment in internal_segments
            ],
            "split_reasons": [
                segment.get("split_reason", "semantic_or_size_boundary")
                for segment in internal_segments
            ],
        }
    return result


def build_segment_batch_prompt(segments: list[dict]) -> str:
    compact_segments = [
        {
            "segment_id": segment.get("segment_id"),
            "content": str(segment.get("content") or "")[:4000],
        }
        for segment in segments
    ]
    return f"""
You will receive a JSON array of already segmented text blocks.

For each block, generate concise card copy only:
- segment_id
- viewpoint
- summary

Return one item for every input segment_id.

Viewpoint requirements:
- 2 to 5 words.
- Short, specific, and suitable for a section card title.
- Prefer a compact noun phrase in Title Case, not a full sentence.
- Do not use generic labels such as Background, Discussion, General, Conclusion, or Mental health.
- Do not include URLs, citations, markdown links, or reference markers.

Summary requirements:
- One concise factual sentence, 8 to 14 words if possible.
- More descriptive than the viewpoint, but short enough for a card preview.
- Represent the whole segment.
- Do not list every detail.
- Do not invent facts.

Segments:
{json.dumps(compact_segments, ensure_ascii=False)}
""".strip()


async def call_llm_for_segments_batch(
    segments: list[dict],
    model: str,
) -> list[dict]:
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not configured.")

    try:
        from openai import AsyncOpenAI
    except ImportError as error:
        raise ImportError("The openai package is required for LLM enrichment.") from error

    client = AsyncOpenAI()
    response = await client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You generate concise section card copy for multiple text segments.",
            },
            {
                "role": "user",
                "content": build_segment_batch_prompt(segments),
            },
        ],
        temperature=0.2,
        response_format=SegmentCardBatchOutput,
        timeout=30,
    )

    parsed = response.choices[0].message.parsed
    if isinstance(parsed, SegmentCardBatchOutput):
        raw_items = [item.model_dump() for item in parsed.items]
    elif isinstance(parsed, dict):
        raw_items = parsed.get("items") or []
    else:
        raise ValueError("Segment card batch response did not match the expected schema.")

    normalized_by_id = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        try:
            segment_id = int(item.get("segment_id"))
        except (TypeError, ValueError):
            continue
        normalized_by_id[segment_id] = validate_card_enrichment(item)

    enriched_segments = []
    for segment in segments:
        segment_id = segment.get("segment_id")
        enrichment = normalized_by_id.get(segment_id)
        if enrichment is None:
            enrichment = fallback_generate_viewpoint_and_summary(segment)
        enriched_segments.append(_apply_enrichment(segment, enrichment))
    return enriched_segments


async def enrich_segments_with_llm(
    segments: list[dict],
    model: str = "gpt-4.1-mini",
    concurrency: int = 5,
    max_retries: int = 3,
) -> list[dict]:
    if not isinstance(segments, list):
        raise ValueError("segments must be a list.")

    if not os.getenv("OPENAI_API_KEY"):
        return [dict(segment) for segment in segments]

    for attempt in range(max(1, max_retries)):
        try:
            return await call_llm_for_segments_batch(segments, model)
        except Exception as error:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

    return [
        _apply_enrichment(segment, fallback_generate_viewpoint_and_summary(segment))
        for segment in segments
    ]


def validate_llm_enrichment(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("LLM enrichment must be a JSON object.")

    viewpoint = _clean_viewpoint(str(data.get("viewpoint") or ""))
    summary = _clean_sentence_for_output(str(data.get("summary") or ""))

    _validate_viewpoint(viewpoint, 0)
    _validate_summary(summary, 0)

    return {
        "viewpoint": viewpoint,
        "summary": summary,
    }


def validate_card_enrichment(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Card enrichment must be a JSON object.")

    viewpoint = _clean_viewpoint(str(data.get("viewpoint") or "")).strip(" .")
    summary = _clean_sentence_for_output(str(data.get("summary") or ""))

    if not viewpoint:
        raise ValueError("Card viewpoint is empty.")
    if not summary:
        raise ValueError("Card summary is empty.")

    lowered = viewpoint.lower().strip(" .")
    if lowered in WEAK_VIEWPOINTS or lowered in REFERENCE_HEADINGS:
        raise ValueError("Card viewpoint is generic.")
    if re.search(r"https?://|www\.|\[[^\]]+\]", f"{viewpoint} {summary}"):
        raise ValueError("Card enrichment contains URL or citation markers.")

    return {
        "viewpoint": viewpoint,
        "summary": summary,
    }


def fallback_generate_viewpoint_and_summary(segment: dict) -> dict:
    content = str(segment.get("content") or "")
    existing = {
        "viewpoint": segment.get("viewpoint"),
        "summary": segment.get("summary"),
    }
    try:
        return validate_llm_enrichment(existing)
    except Exception:
        pass

    return {
        "viewpoint": generate_viewpoint(content),
        "summary": _summarize_segment_local(content),
    }


def _apply_enrichment(segment: dict, enrichment: dict) -> dict:
    enriched_segment = dict(segment)
    enriched_segment["viewpoint"] = enrichment["viewpoint"]
    enriched_segment["summary"] = enrichment["summary"]
    return enriched_segment


def _run_async_enrichment_sync(
    segments: list[dict],
    model: str,
    concurrency: int,
    max_retries: int,
) -> list[dict]:
    if not segments:
        return []

    async def run_enrichment() -> list[dict]:
        return await enrich_segments_with_llm(
            segments,
            model=model,
            concurrency=concurrency,
            max_retries=max_retries,
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run_enrichment())

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(run_enrichment())).result()


def _extract_json_object(content: str) -> dict:
    if not content or not content.strip():
        raise ValueError("LLM response was empty.")

    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as original_error:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise ValueError("LLM response did not contain a JSON object.") from original_error
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as error:
            raise ValueError(f"LLM returned invalid JSON: {error}") from error


def _flush_paragraph(paragraphs: list[str], current: list[str]) -> None:
    if current:
        paragraphs.append(" ".join(current).strip())


def _make_sentence(
    sentence_id: int,
    text: str,
    heading_level: int | None,
    is_heading: bool,
    is_reference: bool,
) -> dict:
    return {
        "sentence_id": sentence_id,
        "text": text,
        "word_count": count_words(text),
        "heading_level": heading_level,
        "is_heading": is_heading,
        "is_reference": is_reference,
    }


def _is_markdown_heading(text: str) -> bool:
    return bool(re.match(r"^\s*#{1,6}\s+\S+", text))


def _heading_level(text: str) -> int | None:
    match = re.match(r"^\s*(#{1,6})\s+\S+", text)
    if match:
        return len(match.group(1))
    return None


def _normalize_heading_text(text: str) -> str:
    text = re.sub(r"^\s*#{1,6}\s+", "", text.strip())
    text = re.sub(r"^\d+(\.\d+)*\.?\s+", "", text)
    return re.sub(r"\s+", " ", text.strip(" :-")).lower()


def _is_reference_heading(text: str) -> bool:
    return _normalize_heading_text(text) in REFERENCE_HEADINGS


def _looks_like_reference_line(text: str) -> bool:
    lowered = text.lower().strip()
    if re.match(r"^\[\d+\]:\s*https?://", lowered):
        return True
    if "http://" in lowered or "https://" in lowered or "www." in lowered:
        return True
    if re.match(r"^\[\d+\]", lowered):
        return True
    return False


def _protect_abbreviations(text: str) -> str:
    protected = text
    for abbreviation in ABBREVIATIONS:
        pattern = re.compile(re.escape(abbreviation), re.IGNORECASE)
        replacement = abbreviation.replace(".", "<PERIOD>")
        protected = pattern.sub(replacement, protected)
    return protected


def _restore_abbreviations(text: str) -> str:
    return text.replace("<PERIOD>", ".")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text.lower())


def _build_tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    tokenized_texts = [_tokenize(text) for text in texts]
    document_count = len(tokenized_texts)
    document_frequency = Counter()

    for tokens in tokenized_texts:
        document_frequency.update(set(tokens))

    vectors = []
    for tokens in tokenized_texts:
        term_frequency = Counter(tokens)
        vector = {}
        for token, count in term_frequency.items():
            idf = math.log((1 + document_count) / (1 + document_frequency[token])) + 1
            vector[token] = count * idf
        vectors.append(vector)

    return vectors


def _cosine_similarity_sparse(
    vector_a: dict[str, float],
    vector_b: dict[str, float],
) -> float:
    if not vector_a or not vector_b:
        return 0.0

    common_terms = set(vector_a) & set(vector_b)
    dot_product = sum(vector_a[term] * vector_b[term] for term in common_terms)
    magnitude_a = math.sqrt(sum(value * value for value in vector_a.values()))
    magnitude_b = math.sqrt(sum(value * value for value in vector_b.values()))

    if not magnitude_a or not magnitude_b:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def _heading_boundaries(sentences: list[dict]) -> list[dict]:
    boundaries = []
    for index, sentence in enumerate(sentences):
        if index == 0 or not sentence.get("is_heading"):
            continue
        previous_sentence = sentences[index - 1]
        if _is_reference_heading(sentence["text"]):
            continue
        strength = 1.5 if sentence.get("heading_level") in {1, 2} else 1.2
        boundaries.append(
            {
                "after_sentence_id": previous_sentence["sentence_id"],
                "before_block_id": None,
                "after_block_id": None,
                "similarity": 0.0,
                "boundary_strength": strength,
                "source": "heading",
            }
        )
    return boundaries


def _merge_boundaries_by_sentence_id(boundaries: list[dict]) -> dict[int, dict]:
    merged = {}
    for boundary in boundaries:
        sentence_id = boundary["after_sentence_id"]
        current = merged.get(sentence_id)
        if current is None or boundary["boundary_strength"] > current["boundary_strength"]:
            merged[sentence_id] = boundary
    return merged


def _select_segment_end_index(
    sentences: list[dict],
    current_start_index: int,
    boundary_by_after_id: dict[int, dict],
    target_words: int,
    min_words: int,
    max_words: int,
) -> int:
    current_words = 0
    min_index = None
    max_index = len(sentences) - 1
    target_index = len(sentences) - 1
    target_distance = float("inf")

    for index in range(current_start_index, len(sentences)):
        current_words += sentences[index]["word_count"]
        distance = abs(current_words - target_words)
        if distance < target_distance:
            target_distance = distance
            target_index = index
        if min_index is None and current_words >= min_words:
            min_index = index
        if current_words <= max_words:
            max_index = index
        if current_words > max_words:
            break

    if min_index is None:
        return len(sentences) - 1

    candidates = []
    early_hard_candidates = []
    candidate_words = 0
    for index in range(current_start_index, max_index + 1):
        candidate_words += sentences[index]["word_count"]
        boundary = boundary_by_after_id.get(sentences[index]["sentence_id"])
        if not boundary:
            continue
        if index >= min_index:
            candidates.append((index, candidate_words, boundary))
        elif boundary.get("source") == "heading" and candidate_words >= min(180, min_words):
            early_hard_candidates.append((index, candidate_words, boundary))

    if candidates:
        return _choose_best_boundary_index(candidates, target_words)
    if early_hard_candidates:
        return _choose_best_boundary_index(early_hard_candidates, target_words)
    return target_index


def _choose_best_boundary_index(
    candidates: list[tuple[int, int, dict]],
    target_words: int,
) -> int:
    best = None
    best_key = None
    strongest = max(candidate[2]["boundary_strength"] for candidate in candidates)

    for index, word_count, boundary in candidates:
        strength = boundary["boundary_strength"]
        close_strength_penalty = 0 if strongest - strength <= 0.05 else strongest - strength
        key = (
            close_strength_penalty,
            abs(word_count - target_words),
            -strength,
        )
        if best_key is None or key < best_key:
            best_key = key
            best = index
    return best


def _make_raw_segment_from_slice(
    sentences: list[dict],
    start_index: int,
    end_index: int,
) -> dict:
    segment_sentences = sentences[start_index : end_index + 1]
    content = " ".join(sentence["text"] for sentence in segment_sentences).strip()
    sentence_ids = [sentence["sentence_id"] for sentence in segment_sentences]
    return {
        "start_sentence_id": sentence_ids[0],
        "end_sentence_id": sentence_ids[-1],
        "sentence_ids": sentence_ids,
        "word_count": count_words(content),
        "content": content,
        "_sentences": segment_sentences,
    }


def _merge_short_final_segment(
    raw_segments: list[dict],
    min_words: int,
    max_words: int,
) -> list[dict]:
    if len(raw_segments) < 2:
        return raw_segments

    last_segment = raw_segments[-1]
    previous_segment = raw_segments[-2]

    if last_segment["word_count"] >= min_words:
        return raw_segments
    if _segment_starts_with_major_heading(last_segment):
        return raw_segments

    merged_word_count = previous_segment["word_count"] + last_segment["word_count"]
    if merged_word_count > max_words * 1.25:
        return raw_segments

    merged_sentences = previous_segment["_sentences"] + last_segment["_sentences"]
    merged_segment = _make_raw_segment_from_slice(
        merged_sentences,
        0,
        len(merged_sentences) - 1,
    )

    return raw_segments[:-2] + [merged_segment]


def _split_segments_with_many_major_headings(
    raw_segments: list[dict],
    min_words: int,
) -> list[dict]:
    refined_segments = []

    for segment in raw_segments:
        segment_sentences = segment["_sentences"]
        major_heading_indices = [
            index
            for index, sentence in enumerate(segment_sentences)
            if _is_major_heading_sentence(sentence)
        ]

        if len(major_heading_indices) < 2:
            refined_segments.append(segment)
            continue

        should_split = len(major_heading_indices) >= 3 or segment["word_count"] >= min_words
        if not should_split:
            refined_segments.append(segment)
            continue

        split_starts = [0]
        for heading_index in major_heading_indices[1:]:
            if heading_index - split_starts[-1] <= 1:
                continue

            previous_words = _sentence_slice_word_count(
                segment_sentences,
                split_starts[-1],
                heading_index - 1,
            )
            remaining_words = _sentence_slice_word_count(
                segment_sentences,
                heading_index,
                len(segment_sentences) - 1,
            )

            if len(major_heading_indices) >= 3:
                split_starts.append(heading_index)
            elif previous_words >= 250 and remaining_words >= 250:
                split_starts.append(heading_index)

        if len(split_starts) == 1:
            refined_segments.append(segment)
            continue

        for position, start in enumerate(split_starts):
            end = split_starts[position + 1] - 1 if position + 1 < len(split_starts) else len(segment_sentences) - 1
            new_segment = _make_raw_segment_from_slice(segment_sentences, start, end)
            new_segment["split_reason"] = "major_heading_boundary"
            refined_segments.append(new_segment)

    return refined_segments


def _segment_starts_with_major_heading(segment: dict) -> bool:
    first_sentence = segment["_sentences"][0]
    return _is_major_heading_sentence(first_sentence)


def _is_major_heading_sentence(sentence: dict) -> bool:
    if not sentence.get("is_heading"):
        return False
    if sentence.get("is_reference"):
        return False
    level = sentence.get("heading_level")
    return level in {1, 2} or _normalize_heading_text(sentence["text"]) in {
        "introduction",
        "conclusion",
        "final thoughts",
        "summary",
    }


def _sentence_slice_word_count(
    sentences: list[dict],
    start_index: int,
    end_index: int,
) -> int:
    return sum(sentence["word_count"] for sentence in sentences[start_index : end_index + 1])


def _has_strong_method_evidence(text: str, headings: list[str]) -> bool:
    if any(heading in {"method", "methods", "methodology"} for heading in headings):
        return True
    strong_terms = (
        "data collection",
        "dataset",
        "participants",
        "experimental setup",
        "study design",
        "evaluation protocol",
        "implementation procedure",
        "algorithm",
        "system architecture",
        "we measured",
        "we implemented",
    )
    return sum(1 for term in strong_terms if term in text) >= 2


def _has_strong_result_evidence(text: str, headings: list[str]) -> bool:
    if any(heading in {"result", "results", "findings"} for heading in headings):
        return True
    strong_terms = (
        "results showed",
        "findings showed",
        "we found",
        "survey results",
        "evaluation results",
        "statistically significant",
        "measured",
        "metrics",
        "observed",
    )
    return sum(1 for term in strong_terms if term in text) >= 2


def _is_summary_candidate(sentence: dict) -> bool:
    text = sentence["text"].strip()
    lowered = text.lower()
    if sentence.get("is_heading") or sentence.get("is_reference"):
        return False
    if count_words(text) < 8:
        return False
    if "http://" in lowered or "https://" in lowered or "www." in lowered:
        return False
    if re.fullmatch(r"[\[\]\d\s,().;:-]+", text):
        return False
    if _citation_count(text) >= 4:
        return False
    if re.match(r"^\[?\d+\]?:", lowered):
        return False
    return True


def _construct_role_viewpoint(
    content: str,
    headings: list[str],
    summary: str,
) -> str:
    text = content.lower()
    main_topic = _extract_main_topic(headings, summary, content)

    if any(heading in {"conclusion", "final thoughts", "summary"} for heading in headings):
        return f"{main_topic} requires sustained care and shared responsibility."
    if re.search(r"\b(prevention|prevent|early support|before crisis)\b", text):
        return "Prevention is better than crisis response."
    if re.search(r"\b(technology|social media|digital)\b", text):
        return "Technology can connect, distract, and exhaust people."
    if re.search(r"\b(school|schools|student|students|bullying|academic pressure)\b", text):
        return "Schools shape well-being through pressure, belonging, and support."
    if re.search(r"\b(access|affordable|therapy|care|services|culturally)\b", text):
        return "Care must be reachable, affordable, and culturally safe."
    if re.search(r"\b(work|workplace|burnout|job)\b", text):
        return "Workplaces can protect or damage mental health."
    if re.search(r"\b(cause|causes|because|risk factor|leads to)\b", text):
        return f"{main_topic} is shaped by connected causes."
    if re.search(r"\b(defined|definition|means|is not only|includes)\b", text):
        return f"{main_topic} is broader than a simple label."
    if re.search(r"\b(challenge|problem|barrier|stigma|inequality)\b", text):
        return f"{main_topic} creates practical and social challenges."
    if re.search(r"\b(solution|support|should|need|needs|must)\b", text):
        return f"{main_topic} needs practical support and action."
    return ""


def _extract_main_topic(headings: list[str], summary: str, content: str) -> str:
    for heading in headings:
        cleaned = _clean_viewpoint(heading)
        normalized = cleaned.lower().strip(" .")
        if normalized in {"conclusion", "final thoughts", "summary"}:
            continue
        if cleaned and normalized not in WEAK_VIEWPOINTS and count_words(cleaned) <= 8:
            cleaned = cleaned.strip(" .")
            return cleaned[:1].upper() + cleaned[1:]

    tokens = [
        token for token in _tokenize(summary or content)
        if token not in STOPWORDS and len(token) > 3
    ]
    if tokens:
        common = Counter(tokens).most_common(2)
        return " ".join(token for token, _ in common).capitalize()
    return "This issue"


def _clean_sentence_for_output(text: str) -> str:
    text = _remove_urls_and_citations(text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _clean_viewpoint(text: str) -> str:
    text = _remove_urls_and_citations(text)
    text = re.sub(r"^\s*#{1,6}\s+", "", text)
    text = re.sub(r"^\d+(\.\d+)*\.?\s+", "", text)
    text = re.sub(r"[*_`>#\[\]():]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -.,;:")

    words = text.split()
    if len(words) > 16:
        text = " ".join(words[:16]).rstrip(" ,;:")
    if text and text[-1] not in ".!?":
        text += "."
    return text[:1].upper() + text[1:] if text else ""


def _remove_urls_and_citations(text: str) -> str:
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\[[^\]]*\]|\(\s*\[\s*\d+\s*\]\s*\)|\(\s*\d{4}\s*\)", "", text)
    text = re.sub(r"\(\s*\)", "", text)
    return text


def _is_valid_viewpoint_text(viewpoint: str, allow_short: bool = False) -> bool:
    if not viewpoint:
        return False
    lowered = viewpoint.lower().strip(" .")
    if lowered in WEAK_VIEWPOINTS:
        return False
    if _looks_like_weak_topic_label(viewpoint):
        return False
    if re.search(r"https?://|www\.|\[[^\]]+\]", viewpoint):
        return False
    word_count = count_words(viewpoint)
    if allow_short:
        return 3 <= word_count <= 20
    return 4 <= word_count <= 20


def _validate_viewpoint(viewpoint: str, segment_id: int) -> None:
    if not viewpoint or not viewpoint.strip():
        raise ValueError(f"Segment {segment_id} has an empty viewpoint.")
    lowered = viewpoint.lower().strip(" .")
    if lowered in WEAK_VIEWPOINTS:
        raise ValueError(f"Segment {segment_id} has a generic viewpoint.")
    if _looks_like_weak_topic_label(viewpoint):
        raise ValueError(f"Segment {segment_id} has a weak topic-label viewpoint.")
    if re.search(r"https?://|www\.|\[[^\]]+\]", viewpoint):
        raise ValueError(f"Segment {segment_id} viewpoint contains URL or citation markers.")
    if count_words(viewpoint) < 3 or count_words(viewpoint) > 22:
        raise ValueError(f"Segment {segment_id} viewpoint length is outside the accepted range.")


def _looks_like_weak_topic_label(viewpoint: str) -> bool:
    cleaned = viewpoint.lower().strip(" .")
    words = cleaned.split()
    if len(words) > 6:
        return False
    verb_markers = {
        "is",
        "are",
        "can",
        "must",
        "should",
        "requires",
        "require",
        "needs",
        "need",
        "shapes",
        "shape",
        "affects",
        "protects",
        "damages",
        "turns",
        "depends",
    }
    return not any(word in verb_markers for word in words)


def _validate_summary(summary: str, segment_id: int) -> None:
    if not summary or not summary.strip():
        raise ValueError(f"Segment {segment_id} has an empty summary.")
    if re.search(r"https?://|www\.|\[[^\]]+\]", summary):
        raise ValueError(f"Segment {segment_id} summary contains URL or citation markers.")


def _citation_count(text: str) -> int:
    return len(re.findall(r"\[[^\]]+\]|\(\s*\d{4}\s*\)", text))


def _sentence_by_id(sentences: list[dict], sentence_id: int) -> dict:
    for sentence in sentences:
        if sentence["sentence_id"] == sentence_id:
            return sentence
    raise ValueError(f"Unknown sentence_id: {sentence_id}")


def _normalize_for_duplicate_check(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _validate_repeated_shingles(content: str, segment_id: int) -> None:
    words = _tokenize(content)
    if len(words) < 80:
        return

    shingles = [
        tuple(words[index : index + 8])
        for index in range(0, len(words) - 7)
    ]
    if not shingles:
        return

    counts = Counter(shingles)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    if repeated > 20 and repeated / len(shingles) > 0.18:
        raise ValueError(f"Segment {segment_id} contains repeated text blocks.")


def _public_segment(segment: dict) -> dict:
    return {
        "segment_id": segment["segment_id"],
        "viewpoint": segment["viewpoint"],
        "summary": segment["summary"],
        "word_count": segment["word_count"],
        "content": segment["content"],
    }


def _empty_debug(sentences: list[dict] | None = None) -> dict:
    sentences = sentences or []
    return {
        "sentence_count": len(sentences),
        "content_sentence_count": len([sentence for sentence in sentences if not sentence.get("is_reference")]),
        "reference_sentence_count": len([sentence for sentence in sentences if sentence.get("is_reference")]),
        "boundaries": [],
        "segment_sentence_ranges": [],
        "segment_viewpoints": [],
        "heading_count_per_segment": [],
        "split_reasons": [],
    }


def _keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if re.search(rf"\b{re.escape(keyword)}\b", text))


def _trim_summary(sentence: str, max_words: int = 35) -> str:
    words = sentence.strip().split()
    if len(words) <= max_words:
        return sentence.strip()
    return " ".join(words[:max_words]).rstrip(" ,;:") + "."


if __name__ == "__main__":
    with open("backend/sample_article.txt", "r", encoding="utf-8", errors="replace") as f:
        sample_text = f.read()
   

    print(preprocess_text(sample_text, fallback_to_tfidf=True, debug=True))
