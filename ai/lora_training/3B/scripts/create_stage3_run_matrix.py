#!/usr/bin/env python
"""Create the Stage 3 run matrix from the Stage 2 top-model selection."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "stage3"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    stage2_path = ROOT / "reports" / "stage2" / "stage2_top_models.json"
    template_path = ROOT / "configs" / "stage3_search_templates.json"
    stage2 = load_json(stage2_path)
    templates = load_json(template_path)
    selected = stage2.get("selected_top_k", [])
    runs: list[dict[str, Any]] = []
    for candidate in selected:
        candidate_key = candidate["candidate"]
        for template in templates["templates"]:
            run_id = template["run_id_suffix"]
            stage_label = template["stage_label_suffix"]
            runs.append(
                {
                    "candidate": candidate_key,
                    "run_id": run_id,
                    "stage_label": stage_label,
                    "epochs": template["epochs"],
                    "learning_rate": template["learning_rate"],
                    "lora_r": template["lora_r"],
                    "lora_alpha": template["lora_alpha"],
                    "lora_dropout": template["lora_dropout"],
                    "training_command": (
                        "bash scripts/run_qlora_training_with_fallback.sh "
                        f"{candidate_key} {run_id} {template['epochs']} {template['learning_rate']} "
                        f"{template['lora_r']} {template['lora_alpha']} {template['lora_dropout']}"
                    ),
                    "postprocess_command": (
                        "bash scripts/postprocess_run_candidate.sh "
                        f"{candidate_key} {run_id} {stage_label} val50_{candidate_key}_{stage_label}"
                    ),
                }
            )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at_utc": utc_now(),
        "source_stage2_selection": str(stage2_path.relative_to(ROOT)),
        "source_templates": str(template_path.relative_to(ROOT)),
        "run_count": len(runs),
        "runs": runs,
    }
    json_path = OUT_DIR / "stage3_run_matrix.json"
    md_path = OUT_DIR / "stage3_run_matrix.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Stage 3 Run Matrix",
        "",
        f"- Created UTC: `{payload['created_at_utc']}`",
        f"- Run count: `{len(runs)}`",
        "",
        "| # | Candidate | Run ID | r | Alpha | LR | Epochs |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for idx, run in enumerate(runs, start=1):
        lines.append(
            f"| {idx} | {run['candidate']} | {run['run_id']} | {run['lora_r']} | {run['lora_alpha']} | {run['learning_rate']} | {run['epochs']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "runs": len(runs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
