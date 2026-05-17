#!/usr/bin/env python
"""Generate an evidence inventory for experiment reporting."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "evidence"
INCLUDE_DIRS = [
    "configs",
    "data/source_snapshot",
    "logs/command_outputs",
    "logs/tests",
    "logs/decisions",
    "model_workspaces",
    "outputs",
    "reports",
    "benchmark_workspace",
]
SKIP_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth"}
MAX_HASH_SIZE_BYTES = 128 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str | None:
    if path.stat().st_size > MAX_HASH_SIZE_BYTES or path.suffix.lower() in SKIP_SUFFIXES:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if "/command_outputs/" in f"/{rel}" or rel.startswith("logs/command_outputs/"):
        return "command_output_log"
    if "/tests/" in f"/{rel}" or rel.startswith("logs/tests/"):
        return "test_or_exit_code"
    if "/decisions/" in f"/{rel}" or rel.startswith("logs/decisions/"):
        return "decision_note"
    if rel.startswith("configs/") or "/configs/" in f"/{rel}":
        return "config"
    if "manifest" in path.name.lower():
        return "manifest"
    if "metrics" in path.name.lower() or "summary" in path.name.lower():
        return "metrics_or_summary"
    if "raw_outputs" in rel:
        return "raw_outputs"
    if "parsed_outputs" in rel:
        return "parsed_outputs"
    if "parse_failures" in rel:
        return "parse_failures"
    if rel.startswith("reports/"):
        return "report"
    return "artifact"


def inventory_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for include in INCLUDE_DIRS:
        base = ROOT / include
        if not base.exists():
            continue
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            rel = path.relative_to(ROOT).as_posix()
            rows.append(
                {
                    "relative_path": rel,
                    "category": classify(path),
                    "size_bytes": path.stat().st_size,
                    "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "sha256": sha256_file(path),
                }
            )
    return rows


def write_markdown(rows: list[dict[str, Any]], path: Path) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    lines = [
        "# Evidence Inventory",
        "",
        f"- Created UTC: `{utc_now()}`",
        f"- Root: `{ROOT}`",
        f"- Files indexed: `{len(rows)}`",
        "",
        "## Category Counts",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"| {category} | {count} |")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "| Category | Size | SHA256 | Path |",
            "|---|---:|---|---|",
        ]
    )
    for row in rows:
        sha = row["sha256"] or "not_hashed_large_or_weight_file"
        lines.append(f"| {row['category']} | {row['size_bytes']} | `{sha}` | `{row['relative_path']}` |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = inventory_rows()
    payload = {
        "created_at_utc": utc_now(),
        "root": str(ROOT),
        "file_count": len(rows),
        "hash_policy": {
            "max_hash_size_bytes": MAX_HASH_SIZE_BYTES,
            "skipped_weight_suffixes": sorted(SKIP_SUFFIXES),
        },
        "files": rows,
    }
    json_path = OUT_DIR / "evidence_inventory.json"
    md_path = OUT_DIR / "evidence_inventory.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(rows, md_path)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "files": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
