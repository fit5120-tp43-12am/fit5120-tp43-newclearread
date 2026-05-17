from __future__ import annotations

from pathlib import Path

from sweep_utils import ROOT, path_manifest, read_json, write_json, write_text


def main() -> int:
    candidate_config = read_json(ROOT / "configs" / "sweep_candidates.json")
    snapshot_files = [
        *Path(ROOT / "data" / "source_snapshot" / "training3b_splits").glob("*"),
        *Path(ROOT / "data" / "source_snapshot" / "base_shootout_reports").glob("*"),
        *Path(ROOT / "data" / "source_snapshot" / "llama3b_optimization_reports").glob("*"),
        ROOT / "configs" / "sweep_candidates.json",
        ROOT / "configs" / "judge_prompt_schema_candidate_v1_1.md",
    ]
    manifest = path_manifest([path for path in snapshot_files if path.is_file()], ROOT)
    manifest["candidate_count"] = len(candidate_config["candidates"])
    manifest["stage1_anchor_defaults"] = candidate_config["stage1_anchor_defaults"]
    write_json(ROOT / "manifests" / "stage0_source_snapshot_manifest.json", manifest)

    readme = "\n".join(
        [
            "# Fine-Tune Sweep Start Here",
            "",
            "This workspace is isolated from earlier iteration folders.",
            "",
            "Rules:",
            "",
            "- Do not delete existing artifacts.",
            "- Treat `iteration1` and `training-3b` as read-only source snapshots.",
            "- Save every config, command log, exit code, training output, validation output, judge output, and decision note.",
            "",
            "Main stages:",
            "",
            "1. Stage 0: preflight and data/script snapshots.",
            "2. Stage 1: 5-epoch anchor curve for every serious 3-4B candidate.",
            "3. Stage 2: select top 3 model families.",
            "4. Stage 3: local parameter search for top 3.",
            "5. Stage 4: finalist refinements.",
            "6. Stage 5: frozen benchmark for final 2.",
            "",
            "Current candidates:",
            "",
            *[f"- `{item['key']}`: `{item['model_id']}`" for item in candidate_config["candidates"]],
            "",
        ]
    )
    write_text(ROOT / "README_START_HERE.md", readme)
    print({"status": "completed", "manifest": str(ROOT / "manifests" / "stage0_source_snapshot_manifest.json")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
