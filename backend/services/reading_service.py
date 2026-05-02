import os
from pathlib import Path

from dotenv import load_dotenv

from services import model_service
from services.text_preprocessor import preprocess_text
from services.text_service import basic_algorithm, use_openai


BACKEND_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(BACKEND_ENV_PATH)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


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
    used_fallback = preprocessing_used_fallback
    fallback_reasons = []
    prepared_blocks = []
    model_results_by_id = {}

    if preprocessing_reason:
        fallback_reasons.append(preprocessing_reason)

    for index, segment in enumerate(segments, start=1):
        block_text = _limit_block_text(segment.get("cleaned_text") or source_text)
        prepared_blocks.append(
            {
                "frontend_id": index,
                "model_id": f"block-{index}",
                "text": block_text,
            }
        )

    model_blocks = prepared_blocks[: model_service.get_summary_max_blocks()]
    if model_blocks:
        try:
            model_response = model_service.summarize_blocks(
                [
                    {"id": block["model_id"], "text": block["text"]}
                    for block in model_blocks
                ]
            )
            model_results_by_id = model_service.normalize_model_results(model_response)
        except Exception:
            used_fallback = True
            fallback_reasons.append("team_model_unavailable")

    blocks = []
    for block in prepared_blocks:
        # Each segment becomes one frontend block. The originalText field keeps the
        # cleaned source content, while summary/keyPoints are generated per block.
        model_result = model_results_by_id.get(block["model_id"])
        used_summary_fallback = False

        if model_result and model_result.get("status") == "ok":
            summary_result = {
                "summary": model_result.get("summary") or "",
                "keyPoints": model_result.get("keyPoints") or [],
                "usedFallback": False,
                "fallbackReason": "",
            }
        else:
            used_summary_fallback = True
            summary_result = _summarise_block_fallback(block["text"])

        if used_summary_fallback or summary_result.get("usedFallback"):
            # Track partial failures without dropping the rest of the blocks.
            used_fallback = True
            reason = _get_summary_fallback_reason(
                block,
                model_blocks,
                model_result,
                summary_result,
            )
            if reason not in fallback_reasons:
                fallback_reasons.append(reason)

        blocks.append(
            {
                "id": block["frontend_id"],
                "originalText": block["text"],
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


def _summarise_block_fallback(text: str) -> dict:
    if _env_bool("CLEARREAD_OPENAI_SUMMARY_FALLBACK", True):
        try:
            return use_openai(text)
        except Exception:
            pass

    return basic_algorithm(
        text,
        notice="AI service is unavailable right now. Showing a basic result.",
        fallback_reason="temporary_ai_unavailable",
    )


def _limit_block_text(text: str) -> str:
    # Truncate very large segments before summary generation to avoid oversized API requests.
    cleaned = str(text or "").strip()
    max_chars = model_service.get_summary_max_chars_per_block()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip()


def _get_summary_fallback_reason(
    block: dict,
    model_blocks: list[dict],
    model_result: dict | None,
    summary_result: dict,
) -> str:
    model_block_ids = {model_block["model_id"] for model_block in model_blocks}
    if block["model_id"] not in model_block_ids:
        return "team_model_block_limit_exceeded"

    if model_result and model_result.get("status") == "error":
        return "team_model_item_error"

    if model_result is None:
        return "team_model_item_missing"

    return summary_result.get("fallbackReason") or "summary_fallback"


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
