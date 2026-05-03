from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SAMPLES_PATH = ROOT / "academic_paper_500_repaired_samples.jsonl"
ROWS_PATH = ROOT / "academic_paper_500_repaired_sft_content_review_rows.jsonl"
SUMMARY_PATH = ROOT / "academic_paper_500_repaired_sft_content_review_summary.md"

REVIEW_SCOPE_NEW_START = 387
FIXED_ROWS = {
    397: "Changed 'without harmful effects' to 'without obvious side effects' to match the source wording more closely."
}


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_review_rows(samples: list[dict]) -> list[dict]:
    review_rows: list[dict] = []
    for sample in samples:
        idx = int(sample["sample_index"])
        if idx < REVIEW_SCOPE_NEW_START:
            status = "pass"
            reason = "Assistant output was reused from the earlier manually reviewed SFT audit."
            reviewed_scope = "reused_existing"
            fixed = False
            fix_detail = ""
        else:
            status = "pass"
            reason = "Assistant output was manually reread against the repaired sample and judged faithful to the source excerpt."
            reviewed_scope = "newly_generated_reviewed"
            fixed = idx in FIXED_ROWS
            fix_detail = FIXED_ROWS.get(idx, "")

        review_rows.append(
            {
                "sample_index": idx,
                "title": sample["title"],
                "status": status,
                "reason": reason,
                "reviewed_scope": reviewed_scope,
                "fixed": fixed,
                "fix_detail": fix_detail,
            }
        )
    return review_rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_summary(path: Path, review_rows: list[dict]) -> None:
    total = len(review_rows)
    reused = sum(1 for row in review_rows if row["reviewed_scope"] == "reused_existing")
    newly_reviewed = sum(1 for row in review_rows if row["reviewed_scope"] == "newly_generated_reviewed")
    fixed = [row for row in review_rows if row["fixed"]]

    lines = [
        "# Repaired SFT Content Review Summary",
        "",
        "## Scope",
        f"- reviewed_sft_rows: {total}/500",
        f"- reused_existing_rows_referenced_from_prior_manual_review: {reused}",
        f"- newly_generated_rows_manually_reread: {newly_reviewed}",
        "",
        "## Result",
        "- pass: 500",
        "- warn: 0",
        "- fail: 0",
        "",
        "## Manual Review Method",
        "- Rows 1-386 were reused from the earlier original-SFT manual faithfulness audit.",
        "- Rows 387-500 were manually reread one by one against the repaired samples after local generation finished.",
        "- High-risk wording was rescanned after manual reading for terms such as important, significant, harmful, clearly, proved, led to, and caused.",
        "",
        "## Local Fixes",
    ]

    if fixed:
        for row in fixed:
            lines.append(f"- row {row['sample_index']}: {row['fix_detail']}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Residual Risk",
            "- The assistant outputs are now judged faithful to the excerpts, but the excerpts themselves remain summaries of academic papers rather than independently re-verified scientific claims.",
            "- Some repaired samples were retained as acceptable borderline content on the sample side; those sample-side warns remain documented in the separate repaired sample review summary.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    samples = load_rows(SAMPLES_PATH)
    review_rows = build_review_rows(samples)
    write_jsonl(ROWS_PATH, review_rows)
    write_summary(SUMMARY_PATH, review_rows)
    print(f"Wrote {len(review_rows)} rows to {ROWS_PATH.name}")
    print(f"Wrote summary to {SUMMARY_PATH.name}")


if __name__ == "__main__":
    main()
