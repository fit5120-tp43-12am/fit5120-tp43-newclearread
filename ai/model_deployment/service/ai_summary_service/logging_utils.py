from __future__ import annotations

import logging
from typing import Iterable


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("clearread.ai_summary_service")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_request_summary(
    logger: logging.Logger,
    request_id: str | None,
    item_ids: Iterable[str],
    text_lengths: Iterable[int],
    status: str,
    latency_ms: int,
    error_codes: Iterable[str],
) -> None:
    logger.info(
        "summarize request_id=%s item_ids=%s text_lengths=%s status=%s latency_ms=%s error_codes=%s",
        request_id or "",
        list(item_ids),
        list(text_lengths),
        status,
        latency_ms,
        list(error_codes),
    )
