#!/usr/bin/env python
"""Lightweight monitor for the phase2 long-running search."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CURRENT_STATUS = ROOT / "logs" / "tests" / "phase2_current_status.json"
MONITOR_STATUS = ROOT / "logs" / "tests" / "phase2_monitor_status.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def newest_log() -> dict[str, Any] | None:
    logs = sorted((ROOT / "logs" / "command_outputs").glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not logs:
        return None
    path = logs[0]
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "size_bytes": path.stat().st_size,
        "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def gpu_status() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
    except Exception as exc:  # pragma: no cover - diagnostic only
        return {"available": False, "error": f"{exc.__class__.__name__}: {exc}"}
    if proc.returncode != 0:
        return {"available": False, "error": proc.stderr.strip()[-500:]}
    rows = []
    for line in proc.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 4:
            rows.append({"name": parts[0], "memory_used_mib": parts[1], "memory_total_mib": parts[2], "utilization_gpu_percent": parts[3]})
    return {"available": True, "rows": rows}


def decision_note(payload: dict[str, Any]) -> Path:
    path = ROOT / "logs" / "decisions" / f"phase2_monitor_progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    lines = [
        "# Phase2 Monitor Progress",
        "",
        f"- Created UTC: `{payload['created_at_utc']}`",
        f"- Phase: `{payload.get('phase')}`",
        f"- Command: `{payload.get('command_name')}`",
        f"- Exit code: `{payload.get('exit_code')}`",
        f"- Latest log: `{(payload.get('latest_log') or {}).get('path')}`",
        f"- GPU: `{payload.get('gpu')}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    current = read_json(CURRENT_STATUS, {})
    previous_monitor = read_json(MONITOR_STATUS, {})
    payload = {
        "created_at_utc": utc_now(),
        "phase": current.get("phase"),
        "command_name": current.get("command_name"),
        "exit_code": current.get("exit_code"),
        "current_status": current,
        "latest_log": newest_log(),
        "gpu": gpu_status(),
    }
    meaningful = (
        payload.get("phase") != previous_monitor.get("phase")
        or payload.get("command_name") != previous_monitor.get("command_name")
        or payload.get("exit_code") != previous_monitor.get("exit_code")
        or (payload.get("latest_log") or {}).get("size_bytes") != (previous_monitor.get("latest_log") or {}).get("size_bytes")
    )
    if meaningful:
        payload["decision_note"] = str(decision_note(payload).relative_to(ROOT))
    write_json(MONITOR_STATUS, payload)
    print(json.dumps({"status": "ok", "meaningful_progress": meaningful, "phase": payload.get("phase"), "command_name": payload.get("command_name")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
