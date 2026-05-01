from services.text_preprocessor import preprocess_text
from services.text_service import basic_algorithm, use_openai


# Keep each block small enough for one summary request.
MAX_BLOCK_CHARS = 11000


def process_reading_text(text: str) -> dict:
    # This is the main service used by the Reading Support page.
    # It converts one raw article into the block-based response expected by the frontend.
    source_text = (text or "").strip()
    if not source_text:
        # Empty input is handled here so the API can return a consistent response shape.
        return {
            "notice": "No text was provided.",
            "usedFallback": True,
            "fallbackReason": "empty_text",
            "segmentation": _build_segmentation_info(
                {},
                True,
                "empty_text",
                0,
            ),
            "blocks": [],
        }

    # The preprocessor cleans the text and splits it into semantic reading segments.
    (
        segments,
        preprocessing_used_fallback,
        preprocessing_reason,
        segmentation_metadata,
    ) = _build_segments(source_text)
    blocks = []
    used_fallback = preprocessing_used_fallback
    fallback_reasons = []

    if preprocessing_reason:
        fallback_reasons.append(preprocessing_reason)

    for index, segment in enumerate(segments, start=1):
        # Each segment becomes one frontend block. The originalText field keeps the
        # cleaned source content, while summary/keyPoints are generated per block.
        block_text = _limit_block_text(segment.get("cleaned_text") or source_text)
        summary_result = _summarise_block(block_text)

        if summary_result.get("usedFallback"):
            # Track partial failures without dropping the rest of the blocks.
            used_fallback = True
            reason = summary_result.get("fallbackReason") or "summary_fallback"
            if reason not in fallback_reasons:
                fallback_reasons.append(reason)

        blocks.append(
            {
                "id": index,
                "originalText": block_text,
                "summary": summary_result.get("summary") or "",
                "keyPoints": summary_result.get("keyPoints") or [],
            }
        )

    return {
        "notice": _build_notice(used_fallback, fallback_reasons),
        "usedFallback": used_fallback,
        "fallbackReason": ",".join(fallback_reasons),
        "segmentation": _build_segmentation_info(
            segmentation_metadata,
            preprocessing_used_fallback,
            preprocessing_reason,
            len(blocks),
        ),
        "blocks": blocks,
    }


def _build_segments(text: str) -> tuple[list[dict], bool, str, dict]:
    # Use semantic preprocessing first. If it fails, keep the page usable by treating
    # the whole input as a single block.
    preprocessing_result = preprocess_text(text)
    if preprocessing_result.get("status") == "success":
        segments = preprocessing_result.get("segments") or []
        metadata = preprocessing_result.get("metadata") or {}
        used_local_fallback = metadata.get("segmentation_mode") == "local_fallback"
        valid_segments = [
            segment
            for segment in segments
            if isinstance(segment, dict) and str(segment.get("cleaned_text") or "").strip()
        ]
        if valid_segments:
            if used_local_fallback:
                return valid_segments, True, "local_segmentation_fallback", metadata
            return valid_segments, False, "", metadata

    metadata = preprocessing_result.get("metadata") or {}
    return [{"segment_id": 1, "cleaned_text": text}], True, "preprocessing_failed", metadata


def _summarise_block(text: str) -> dict:
    # OpenAI is the temporary external summary provider until the project model is ready.
    try:
        return use_openai(text)
    except Exception:
        # If the external provider is unavailable, generate a simple local result.
        return basic_algorithm(
            text,
            notice="AI service is unavailable right now. Showing a basic result.",
            fallback_reason="temporary_ai_unavailable",
        )


def _limit_block_text(text: str) -> str:
    # Truncate very large segments before summary generation to avoid oversized API requests.
    cleaned = str(text or "").strip()
    if len(cleaned) <= MAX_BLOCK_CHARS:
        return cleaned
    return cleaned[:MAX_BLOCK_CHARS].rstrip()


def _build_notice(used_fallback: bool, fallback_reasons: list[str]) -> str:
    # Choose a short user-facing status message for the frontend result banner.
    if not used_fallback:
        return "Text processed successfully."

    if "preprocessing_failed" in fallback_reasons:
        return "Text was processed without semantic segmentation."

    if "local_segmentation_fallback" in fallback_reasons:
        return "Text was segmented locally because AI segmentation is unavailable."

    return "AI service is unavailable right now. Showing a basic result."


def _build_segmentation_info(
    metadata: dict,
    used_fallback: bool,
    fallback_reason: str,
    segment_count: int,
) -> dict:
    mode = metadata.get("segmentation_mode") or ""
    reason = metadata.get("fallback_reason") or fallback_reason or "ok"
    detail = metadata.get("processing_notes") or ""

    if mode == "sentence_range" and not used_fallback:
        source = "ai"
        reason = "ai_sentence_range_success"
        detail = detail or "AI sentence-range segmentation succeeded."
    elif mode == "local_fallback":
        source = "local_fallback"
        detail = detail or "Local fallback segmentation was used."
    elif fallback_reason == "preprocessing_failed":
        source = "single_block_fallback"
        reason = "preprocessing_failed"
        detail = metadata.get("error") or "AI preprocessing failed and no local segments were available."
    elif fallback_reason == "empty_text":
        source = "none"
        reason = "empty_text"
        detail = "No text was provided."
    else:
        source = "unknown"
        detail = detail or metadata.get("error") or "Segmentation source could not be determined."

    return {
        "source": source,
        "mode": mode or source,
        "reason": reason,
        "detail": detail,
        "segmentCount": segment_count,
        "model": metadata.get("model") or "",
    }
