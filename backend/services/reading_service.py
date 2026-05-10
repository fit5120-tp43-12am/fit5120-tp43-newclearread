import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from services import model_service
from services.overall_summary_service import generate_overall_summary
from services.text_preprocessor import preprocess_text
from services.text_service import basic_algorithm, use_openai


BACKEND_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(BACKEND_ENV_PATH)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def process_reading_text(text: str) -> dict:
    # This is the main service used by the Reading Support page.
    # It converts one raw article into the block-based response expected by the frontend.
    preprocess_seconds = 0.0
    overall_summary_seconds = 0.0
    team_model_seconds = 0.0
    total_start = time.perf_counter()
    timing_enabled = _env_bool("CLEARREAD_READING_TIMING_LOGS", False)

    source_text = (text or "").strip()
    if not source_text:
        # Empty input is handled here so the API can return a consistent response shape.
        _log_reading_timing(
            timing_enabled,
            time.perf_counter() - total_start,
            preprocess_seconds,
            overall_summary_seconds,
            team_model_seconds,
            block_count=0,
            model_block_count=0,
            fallback_block_count=0,
            block_word_counts=[],
        )
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
            "processingStats": _build_processing_stats(
                total_seconds=time.perf_counter() - total_start,
                overall_summary_seconds=overall_summary_seconds,
                preprocess_seconds=preprocess_seconds,
                team_model_seconds=team_model_seconds,
                block_count=0,
                model_block_count=0,
                fallback_block_count=0,
                block_word_counts=[],
            ),
        }

    overall_summary_start = time.perf_counter()
    overall_summary = generate_overall_summary(source_text)
    overall_summary_seconds = time.perf_counter() - overall_summary_start

    # The preprocessor cleans the text and splits it into semantic reading segments.
    preprocess_start = time.perf_counter()
    (
        segments,
        preprocessing_used_fallback,
        preprocessing_reason,
        segmentation_metadata,
    ) = _build_segments(source_text)
    preprocess_seconds = time.perf_counter() - preprocess_start

    used_fallback = preprocessing_used_fallback
    fallback_reasons = []
    prepared_blocks = []
    model_results_by_id = {}

    if preprocessing_reason:
        fallback_reasons.append(preprocessing_reason)

    for index, segment in enumerate(segments, start=1):
        display_text = str(segment.get("cleaned_text") or source_text).strip()
        prepared_blocks.append(
            {
                "frontend_id": index,
                "model_id": f"block-{index}",
                "title": str(segment.get("viewpoint") or "").strip(),
                "subtitle": str(segment.get("segment_summary") or "").strip(),
                "original_text": display_text,
                "summary_text": _limit_block_text(display_text),
            }
        )

    model_enabled = model_service.is_summary_model_enabled()
    model_blocks = (
        prepared_blocks[: model_service.get_summary_max_blocks()] if model_enabled else []
    )
    if model_blocks:
        team_model_start = time.perf_counter()
        try:
            model_response = model_service.summarize_blocks(
                [
                    {"id": block["model_id"], "text": block["summary_text"]}
                    for block in model_blocks
                ]
            )
            model_results_by_id = model_service.normalize_model_results(model_response)
        except Exception:
            used_fallback = True
            fallback_reasons.append("team_model_unavailable")
        finally:
            team_model_seconds = time.perf_counter() - team_model_start

    fallback_blocks = []
    model_summaries_by_id = {}
    for block in prepared_blocks:
        model_result = model_results_by_id.get(block["model_id"])
        if _has_valid_model_summary(model_result):
            model_summaries_by_id[block["model_id"]] = {
                "summary": str(model_result.get("summary") or "").strip(),
                "keyPoints": model_result.get("keyPoints") or [],
                "usedFallback": False,
                "fallbackReason": "",
            }
        else:
            fallback_blocks.append(block)

    fallback_results_by_id = _summarise_fallback_blocks(fallback_blocks)

    blocks = []
    for block in prepared_blocks:
        # Each segment becomes one frontend block. The originalText field keeps the
        # cleaned source content, while summary/keyPoints are generated per block.
        model_result = model_results_by_id.get(block["model_id"])
        used_summary_fallback = block["model_id"] in fallback_results_by_id
        summary_result = model_summaries_by_id.get(block["model_id"])
        if summary_result is None:
            summary_result = fallback_results_by_id.get(block["model_id"]) or {}

        if used_summary_fallback or summary_result.get("usedFallback"):
            # Track partial failures without dropping the rest of the blocks.
            used_fallback = True
            reason = _get_summary_fallback_reason(
                block,
                model_enabled,
                model_blocks,
                model_result,
                summary_result,
            )
            if reason not in fallback_reasons:
                fallback_reasons.append(reason)

        blocks.append(
            {
                "id": block["frontend_id"],
                "title": block["title"],
                "subtitle": block["subtitle"],
                "originalText": block["original_text"],
                "summary": summary_result.get("summary") or "",
                "keyPoints": summary_result.get("keyPoints") or [],
            }
        )

    block_word_counts = [
        _count_words(block.get("originalText") or "") for block in blocks
    ]

    _log_reading_timing(
        timing_enabled,
        time.perf_counter() - total_start,
        preprocess_seconds,
        overall_summary_seconds,
        team_model_seconds,
        block_count=len(blocks),
        model_block_count=len(model_blocks),
        fallback_block_count=len(fallback_blocks),
        block_word_counts=block_word_counts,
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
        "overallSummary": overall_summary,
        "blocks": blocks,
        "processingStats": _build_processing_stats(
            total_seconds=time.perf_counter() - total_start,
            overall_summary_seconds=overall_summary_seconds,
            preprocess_seconds=preprocess_seconds,
            team_model_seconds=team_model_seconds,
            block_count=len(blocks),
            model_block_count=len(model_blocks),
            fallback_block_count=len(fallback_blocks),
            block_word_counts=block_word_counts,
        ),
    }


def _normalize_preprocess_result(preprocessing_result: dict) -> tuple[list[dict], bool, dict]:
    if not isinstance(preprocessing_result, dict):
        return [], False, {}

    raw_segments = preprocessing_result.get("segments") or []
    normalized_segments = []
    for segment in raw_segments:
        if not isinstance(segment, dict):
            continue

        cleaned_text = str(segment.get("cleaned_text") or segment.get("content") or "").strip()
        if not cleaned_text:
            continue

        normalized_segments.append(
            {
                "segment_id": segment.get("segment_id") or len(normalized_segments) + 1,
                "cleaned_text": cleaned_text,
                "viewpoint": str(segment.get("viewpoint") or "").strip(),
                "segment_summary": str(segment.get("summary") or "").strip(),
            }
        )

    metadata = preprocessing_result.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    # text_preprocessor currently returns segments/debug but no status/metadata.
    debug_info = preprocessing_result.get("debug")
    if isinstance(debug_info, dict):
        split_reasons = debug_info.get("split_reasons") or []
        if any(reason == "semantic_or_size_boundary" for reason in split_reasons):
            metadata.setdefault("segmentation_mode", "sentence_range")
        else:
            metadata.setdefault(
                "segmentation_mode",
                "sentence_range" if len(normalized_segments) > 1 else "single_block",
            )
        metadata.setdefault("processing_notes", "derived_from_preprocessor_debug")
    else:
        metadata.setdefault(
            "segmentation_mode",
            "sentence_range" if len(normalized_segments) > 1 else "single_block",
        )
        metadata.setdefault("processing_notes", "normalized_from_preprocess_output")

    metadata.setdefault("fallback_reason", "")

    # Backward compatibility:
    # - old shape: {"status":"success","segments":[...]}
    # - new shape: {"segments":[...]}
    status = preprocessing_result.get("status")
    success = (status == "success") if status is not None else bool(normalized_segments)
    return normalized_segments, success, metadata


def _build_segments(text: str) -> tuple[list[dict], bool, str, dict]:
    # Use semantic preprocessing first. If it fails, keep the page usable by treating
    # the whole input as a single block.
    try:
        preprocessing_result = preprocess_text(text)
    except Exception:
        return [{"segment_id": 1, "cleaned_text": text}], True, "preprocessing_failed", {}

    segments, success, metadata = _normalize_preprocess_result(preprocessing_result)
    if success and segments:
        segmentation_mode = metadata.get("segmentation_mode")
        used_segmentation_fallback = segmentation_mode in {
            "local_fallback",
            "chunked_mixed_fallback",
        }
        if used_segmentation_fallback:
            return (
                segments,
                True,
                metadata.get("fallback_reason") or "local_segmentation_fallback",
                metadata,
            )
        return segments, False, "", metadata

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


def _summarise_fallback_blocks(blocks: list[dict]) -> dict:
    if not blocks:
        return {}

    max_workers = max(1, _env_int("CLEARREAD_OPENAI_FALLBACK_CONCURRENCY", 6))
    max_workers = min(max_workers, len(blocks))

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_block = {
            executor.submit(_summarise_block_fallback, block["summary_text"]): block
            for block in blocks
        }
        for future in as_completed(future_to_block):
            block = future_to_block[future]
            try:
                results[block["model_id"]] = future.result()
            except Exception:
                results[block["model_id"]] = basic_algorithm(
                    block["summary_text"],
                    notice="AI service is unavailable right now. Showing a basic result.",
                    fallback_reason="temporary_ai_unavailable",
                )

    return results


def _has_valid_model_summary(model_result: dict | None) -> bool:
    if not model_result or model_result.get("status") != "ok":
        return False

    summary = str(model_result.get("summary") or "").strip()
    key_points = model_result.get("keyPoints") or []
    return bool(summary and key_points)


def _log_reading_timing(
    enabled: bool,
    total_seconds: float,
    preprocess_seconds: float,
    overall_summary_seconds: float,
    team_model_seconds: float,
    block_count: int,
    model_block_count: int,
    fallback_block_count: int,
    block_word_counts: list[int] | None = None,
) -> None:
    if not enabled:
        return

    block_word_counts = block_word_counts or []
    print(
        "[reading pipeline] "
        f"total={total_seconds:.2f}s "
        f"overall_summary={overall_summary_seconds:.2f}s "
        f"preprocess={preprocess_seconds:.2f}s "
        f"team_model={team_model_seconds:.2f}s "
        f"blocks={block_count} "
        f"model_blocks={model_block_count} "
        f"fallback_blocks={fallback_block_count} "
        f"block_words={block_word_counts}",
        flush=True,
    )


def _build_processing_stats(
    total_seconds: float,
    overall_summary_seconds: float,
    preprocess_seconds: float,
    team_model_seconds: float,
    block_count: int,
    model_block_count: int,
    fallback_block_count: int,
    block_word_counts: list[int],
) -> dict:
    return {
        "totalSeconds": round(total_seconds, 2),
        "overallSummarySeconds": round(overall_summary_seconds, 2),
        "preprocessSeconds": round(preprocess_seconds, 2),
        "modelSeconds": round(team_model_seconds, 2),
        "blockCount": block_count,
        "modelBlockCount": model_block_count,
        "fallbackBlockCount": fallback_block_count,
        "blockWordCounts": block_word_counts,
    }


def _count_words(text: str) -> int:
    # Simple word count for checking block size in logs.
    return len(re.findall(r"\S+", str(text or "")))


def _limit_block_text(text: str) -> str:
    # Truncate very large segments before summary generation to avoid oversized API requests.
    cleaned = str(text or "").strip()
    max_chars = model_service.get_summary_max_chars_per_block()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip()


def _get_summary_fallback_reason(
    block: dict,
    model_enabled: bool,
    model_blocks: list[dict],
    model_result: dict | None,
    summary_result: dict,
) -> str:
    if not model_enabled:
        return summary_result.get("fallbackReason") or "summary_fallback"

    model_block_ids = {model_block["model_id"] for model_block in model_blocks}
    if block["model_id"] not in model_block_ids:
        return "team_model_block_limit_exceeded"

    if model_result and model_result.get("status") == "error":
        return "team_model_item_error"

    if model_result and model_result.get("status") == "ok":
        return "team_model_item_empty"

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

    if "ai_segmentation_failed" in fallback_reasons:
        return "Text was segmented locally because AI segmentation is unavailable."

    if "partial_ai_segmentation_failed" in fallback_reasons:
        return "Some text was segmented locally because AI segmentation was partially unavailable."

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

    if mode in {"sentence_range", "chunked_sentence_range"} and not used_fallback:
        source = "ai"
        reason = "ai_sentence_range_success"
        detail = detail or "AI sentence-range segmentation succeeded."
    elif mode == "local_fallback":
        source = "local_fallback"
        detail = metadata.get("error") or detail or "Local fallback segmentation was used."
    elif mode == "chunked_mixed_fallback":
        source = "mixed"
        detail = metadata.get("error") or detail or "Some chunks used local fallback."
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
