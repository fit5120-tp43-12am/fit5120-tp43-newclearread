from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STATUS_JSON = ROOT / "logs" / "tests" / "phase2_current_status.json"
EVENTS_JSONL = ROOT / "logs" / "tests" / "phase2_events.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def update_status(**payload: Any) -> dict[str, Any]:
    status = {
        "updated_at_utc": utc_now(),
        **payload,
    }
    write_json(STATUS_JSON, status)
    append_jsonl(EVENTS_JSONL, status)
    return status
