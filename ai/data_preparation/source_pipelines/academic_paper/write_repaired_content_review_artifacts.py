from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


def normalize_title_key(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z]+", " ", value.lower())).strip()


WARN_BY_TITLE = {
    normalize_title_key("Should we be screening for ovarian cancer?"): (
        "warn",
        "Viewpoint-style clinical discussion; coherent and single-source, but less empirical than the median row.",
    ),
    normalize_title_key("Outside-In: Entangled Openness as Subversion Influencing Emergent Change"): (
        "warn",
        "Explicitly framed as an opinion piece; kept because the prose is coherent and on-domain.",
    ),
    normalize_title_key("DESIGN AND EVALUATION FRAMEWORK FOR RELEVANT CHEMISTRY-RELATED EDUCATIONAL CARD AND BOARD GAMES"): (
        "warn",
        "Cross-disciplinary education/chemistry content; accepted as education-focused SSH material.",
    ),
    normalize_title_key("Analysis on the Construction Strategy of Building Electrical Engineering with Intelligent Technology"): (
        "warn",
        "Generic engineering prose and lighter evidence density than stronger CSE rows.",
    ),
    normalize_title_key("Perfectionism in occupational science students: occupational therapy implications"): (
        "warn",
        "Student wellbeing topic sits near the health-education boundary, but the body text remains education-focused.",
    ),
    normalize_title_key(
        "Desperately seeking reductions in health inequalities: perspectives of UK researchers on past, present and future directions in health inequalities research"
    ): (
        "warn",
        "Meta-research symposium/focus-group article rather than a standard single-study paper, but coherent and on-domain.",
    ),
    normalize_title_key("Perception on the Animal Fable 'Bird of Paradise' Song"): (
        "warn",
        "Small-sample classroom study with minor title rendering artefacts observed in console output.",
    ),
    normalize_title_key(
        "The dialogical theology of Hans Kung: Clash between the Catholic mission and Islamic Da'wah in Indonesia"
    ): (
        "warn",
        "Dense theology article with minor title rendering artefacts observed in console output.",
    ),
    normalize_title_key(
        "Port Sustainability as a Service: The Design of Bespoke Service Level Agreements SLAs to Improve Operational Efficiency at Harbours by Prioritising Social Satisfaction"
    ): (
        "warn",
        "Mixed business and technical framing around IoT and SLAs; retained as operations-management-adjacent business content.",
    ),
    normalize_title_key("Strategic Planning: Magic-Bullet or Sleight of Hand"): (
        "warn",
        "Essay-like managerial commentary tone; coherent, but less empirical than most BFE rows.",
    ),
    normalize_title_key("The Fashion Industry and its Problematic Consequences in the Green Marketing Era a Review"): (
        "warn",
        "Narrative review framing and somewhat generic phrasing, though still coherent and on-domain.",
    ),
    normalize_title_key(
        "Performance evaluation of yarn raw materials supplier using fuzzy data envelopment analysis approach case study Batik Fabric Company in Sleman"
    ): (
        "warn",
        "English phrasing is weaker than the median row, but the excerpt remains understandable and on-domain.",
    ),
}


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    repaired_samples = load_jsonl(base_dir / "academic_paper_500_repaired_samples.jsonl")
    repaired_outputs = load_jsonl(base_dir / "academic_paper_500_repaired_outputs.jsonl")

    review_rows: list[dict] = []
    for row in repaired_samples:
        sample_index = int(row["sample_index"])
        title = str(row["title"])
        normalized_title = normalize_title_key(title)
        if sample_index <= 386:
            status = "pass"
            reason = "Retained original pass row from the prior full manual review of the original 500-row dataset."
            fixed = False
            repair_action = ""
            review_basis = "prior_full_manual_review_of_original_samples"
        else:
            status, reason = WARN_BY_TITLE.get(
                normalized_title,
                (
                    "pass",
                    "Replacement sample manually reviewed after rebuild; accepted as coherent single-source in-domain prose.",
                ),
            )
            fixed = True
            repair_action = (
                "Replaced an original fail/warn row with a newly extracted single-paper excerpt selected under stricter review-guided filters."
            )
            review_basis = "manual_review_of_replacement_sample_after_rebuild"

        review_rows.append(
            {
                "row": sample_index,
                "sample_index": sample_index,
                "paper_id": row["paper_id"],
                "title": title,
                "domain_key": row["domain_key"],
                "bucket": row["bucket"],
                "status": status,
                "reason": reason,
                "fixed_in_repaired_dataset": fixed,
                "repair_action": repair_action,
                "review_basis": review_basis,
            }
        )

    status_counts = Counter(row["status"] for row in review_rows)
    warn_rows = [row for row in review_rows if row["status"] == "warn"]

    rows_path = base_dir / "academic_paper_500_repaired_content_review_rows.jsonl"
    summary_path = base_dir / "academic_paper_500_repaired_content_review_summary.md"
    write_jsonl(rows_path, review_rows)

    summary_lines = [
        "# Repaired Academic Paper Content Review Summary",
        "",
        "## Final Files",
        f"- Repaired samples: `{base_dir / 'academic_paper_500_repaired_samples.jsonl'}`",
        f"- Seeded repaired raw outputs: `{base_dir / 'academic_paper_500_repaired_outputs.jsonl'}`",
        f"- Replacement-only samples: `{base_dir / 'academic_paper_500_replacements_only.jsonl'}`",
        f"- Review rows: `{rows_path}`",
        "",
        "## Review Coverage",
        "- Original canonical samples previously read manually: 500/500.",
        "- Original canonical SFT rows previously read manually: 500/500.",
        "- Repaired sample rows covered here: 500/500.",
        "- Retained original rows: 386 pass rows inherited from the prior full manual review.",
        "- Replacement rows manually reviewed during the repair pass: 114/114.",
        "- Repaired SFT generation status in this conversation: not yet generated.",
        "",
        "## Sample-Level Status Counts",
        f"- pass: {status_counts.get('pass', 0)}",
        f"- warn: {status_counts.get('warn', 0)}",
        f"- fail: {status_counts.get('fail', 0)}",
        "",
        "## Repair Actions Completed",
        "- Removed all original warn/fail rows from the original canonical 500-row dataset and backfilled them from source with stricter review-guided extraction rules.",
        "- Hardened title normalization so previously rejected bad titles do not return through punctuation or mojibake variants.",
        "- Added extra text rejection rules for obvious figure markers, article-history fragments, and lowercase fragment starts after the title.",
        "- Reseeded repaired raw outputs so the future SFT build can reuse the 386 kept outputs and generate only the 114 replacement labels.",
        "",
        "## Residual Sample Risks",
        "- A small number of accepted rows remain borderline and are marked `warn` below; they are coherent and in-scope enough to keep, but are less ideal than the median row.",
        "",
        "## Warn Rows",
    ]

    if warn_rows:
        for row in warn_rows:
            summary_lines.append(
                f"- `{row['sample_index']}` `{row['title']}`: {row['reason']}"
            )
    else:
        summary_lines.append("- None.")

    summary_lines.extend(
        [
            "",
            "## Local API Generation Command",
            "API 调用未在本对话中执行。",
            "以下脚本和命令已经准备好，可由用户本地执行。",
            "",
            "在当前目录运行：",
            "```powershell",
            "py -3 .\\build_academic_paper_sft_outputs.py --input .\\academic_paper_500_repaired_samples.jsonl --raw-output .\\academic_paper_500_repaired_outputs.jsonl --sft-output .\\academic_paper_500_repaired_sft.jsonl --meta-output .\\academic_paper_500_repaired_sft.meta.json",
            "```",
            "",
            "预期行为：",
            "- 复用 `academic_paper_500_repaired_outputs.jsonl` 中已经 seeded 的 386 条旧标签。",
            "- 仅为 114 条 replacement rows 新生成 assistant 标签。",
            "- 生成 `academic_paper_500_repaired_sft.jsonl` 和 `academic_paper_500_repaired_sft.meta.json`。",
            "",
            "生成后验证命令：",
            "```powershell",
            "py -3 .\\validate_academic_paper_jsonl.py --samples .\\academic_paper_500_repaired_samples.jsonl --sft .\\academic_paper_500_repaired_sft.jsonl",
            "```",
            "",
            "## Remaining Required Review After API Run",
            "- The newly generated repaired SFT rows for sample indices `387-500` still need row-by-row manual faithfulness review before final training sign-off.",
        ]
    )

    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"Wrote repaired review rows to {rows_path}")
    print(f"Wrote repaired review summary to {summary_path}")
    print(f"seeded_raw_output_rows={len(repaired_outputs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
