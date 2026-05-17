#!/usr/bin/env python
"""Verify workspace isolation expectations for the sweep artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OLD_READ_ONLY_ROOTS = [
    Path(r"C:\Users\Aufb\Desktop\fit5120\iteration1"),
    Path(r"C:\Users\Aufb\Desktop\fit5120\iteration1\training-3b"),
]
OUT_PATH = ROOT / "reports" / "compliance" / "workspace_compliance_report.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def collect_known_artifact_paths() -> list[Path]:
    roots = [
        ROOT / "configs",
        ROOT / "scripts",
        ROOT / "data",
        ROOT / "cache",
        ROOT / "model_workspaces",
        ROOT / "outputs",
        ROOT / "logs",
        ROOT / "reports",
        ROOT / "benchmark_workspace",
    ]
    paths: list[Path] = []
    for root in roots:
        if root.exists():
            paths.extend(path for path in root.rglob("*") if path.is_file())
    return paths


def main() -> int:
    artifact_paths = collect_known_artifact_paths()
    outside = [str(path) for path in artifact_paths if not is_inside(path, ROOT)]
    payload: dict[str, Any] = {
        "created_at_utc": utc_now(),
        "workspace_root": str(ROOT),
        "old_read_only_roots_declared": [str(path) for path in OLD_READ_ONLY_ROOTS],
        "known_artifact_file_count": len(artifact_paths),
        "known_artifacts_outside_workspace": outside,
        "known_artifacts_all_inside_workspace": len(outside) == 0,
        "note": "This verifies known sweep artifact paths. It does not inspect every possible filesystem event that occurred before the report was generated.",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT_PATH), "all_inside": payload["known_artifacts_all_inside_workspace"], "files": len(artifact_paths)}, indent=2))
    return 0 if not outside else 1


if __name__ == "__main__":
    raise SystemExit(main())
