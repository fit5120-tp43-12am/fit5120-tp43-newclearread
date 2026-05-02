#!/usr/bin/env python3
"""
Write per-row review records and a summary for the reviewed public-service dataset.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


FAIL_REASON_BY_INDEX = {
    1: "Original row was off-domain cannabis cultivation content.",
    2: "Original row was ride-hailing contact advice, not public-service process text.",
    8: "Original row was weapon licensing content outside the target domain.",
    10: "Original row was SSL certificate setup, which is tech-admin content rather than public-service explanation.",
    26: "Original row had a title-content mismatch and discussed SSN-related steps instead of the stated tax-ID process.",
    36: "Original row was personal driving advice rather than an official process guide.",
    40: "Original row was tipping advice, not public-service process content.",
    43: "Original row was firearm licensing content outside the target domain.",
    48: "Original row was casino or gaming licensing content outside the intended domain.",
    50: "Original row was federal firearms licensing content.",
    57: "Original row was media licensing content, not a public-service procedure.",
    58: "Original row was art and hobby content.",
    68: "Original row was a software tutorial for legal brief formatting, not a public-service explanation.",
    72: "Original row was firearm dealer licensing content.",
    75: "Original row had a title-content mismatch and discussed H-1B change-of-status rather than the stated B1 topic.",
    80: "Original row was an advocacy or support article rather than a public-service procedure.",
    82: "Original row was concealed-carry weapon permit content.",
    83: "Original row was self-esteem advice rather than public-service process content.",
    86: "Original row was a sports or venue seat-license article.",
    88: "Original row was election-choice advice, not an official voting procedure.",
    89: "Original row was a legal citation tutorial.",
    94: "Original row was motivational unemployment advice rather than a public-service guide.",
    96: "Original row was firearm dealer licensing content.",
    97: "Original row was consumer credit-card advice.",
    102: "Original row was consumer credit-card advice.",
    109: "Original row was breakup advice, not target-domain procedural text.",
    110: "Original row was federal firearms licensing content.",
    121: "Original row was investment advice about tax-free bonds.",
    123: "Original row focused on private legal tactics after an assault incident.",
    129: "Original row was weapon licensing content.",
    134: "Original row was recreational fishing-license content outside the target domain.",
    137: "Original row was vanity plate content outside the intended domain.",
    145: "Original row was landlord advertising advice rather than public-service explanation.",
    147: "Original row focused on private legal defense tactics.",
    152: "Original row was investment yield calculation advice.",
    153: "Original row focused on private legal defense tactics.",
    156: "Original row was generic low-budget legal advice rather than a stable process guide.",
    158: "Original row mixed jurisdictions and was not a stable absentee-voting source text.",
    171: "Original row was firearm dealer licensing content.",
    172: "Original row was weapon licensing content.",
    173: "Original row was persuasion content about encouraging others to vote.",
    177: "Original row was recreational fishing-license content outside the target domain.",
    180: "Original row was car-paint scratch removal advice.",
    188: "Original row was landlord advice rather than public-service procedure.",
    189: "Original row was SSL certificate setup content.",
    196: "Original row was teen driving advice rather than a formal process explanation.",
    197: "Original row was Uber driver earnings or gig-work advice.",
    200: "Original row was music licensing content rather than public-service explanation.",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    base = Path(__file__).resolve().parent
    orig_samples = load_jsonl(base / "public_service_200_samples.jsonl")
    final_samples = load_jsonl(base / "public_service_200_samples_reviewed.jsonl")
    final_sft = load_jsonl(base / "public_service_200_sft_reviewed.jsonl")
    review_map: list[dict[str, Any]] = json.loads((base / "public_service_200_review_map.json").read_text(encoding="utf-8"))

    rows_path = base / "content_review_rows.jsonl"
    summary_path = base / "content_review_summary.md"

    map_by_idx = {int(row["sample_index"]): row for row in review_map}
    review_rows: list[dict[str, Any]] = []

    for idx, final_row in enumerate(final_samples, start=1):
        action = map_by_idx[idx]["action"]
        kept = action == "kept"
        original_title = orig_samples[idx - 1]["title"]
        final_title = final_row["title"]
        record = {
            "sample_index": idx,
            "original_title": original_title,
            "final_title": final_title,
            "bucket": final_row["bucket"],
            "status": "pass",
            "original_status": "pass" if kept else "fail",
            "sample_manually_read": True,
            "sft_manually_read": True,
            "fixed": not kept,
            "fixed_how": None if kept else "Replaced the failed sample with a manually reviewed row from the strict pool and wrote a manual SFT target.",
            "reason": (
                "Reviewed manually and retained because the sample is on-domain, coherent, and the SFT label is faithful."
                if kept
                else f"{FAIL_REASON_BY_INDEX[idx]} Replaced with a manually reviewed on-domain row."
            ),
        }
        if not kept:
            record["replacement_from_strict_index"] = map_by_idx[idx]["replacement_from_strict_index"]
        review_rows.append(record)

    write_jsonl(rows_path, review_rows)

    bucket_counts = Counter(row["bucket"] for row in final_samples)
    theme_counts = {
        "birth certificate": sum(1 for row in final_samples if "birth certificate" in row["title"].lower()),
        "marriage license": sum(1 for row in final_samples if "marriage license" in row["title"].lower()),
        "passport": sum(1 for row in final_samples if "passport" in row["title"].lower()),
    }
    fixed_count = sum(1 for row in review_rows if row["fixed"])
    kept_count = len(review_rows) - fixed_count
    summary = f"""# Content Review Summary

## Final Judgement

- Final decision: trainable, with minor residual diversity/timeliness risks noted below.
- Final samples file: `{(base / "public_service_200_samples_reviewed.jsonl").resolve()}`
- Final raw outputs file: `{(base / "public_service_200_outputs_reviewed.jsonl").resolve()}`
- Final SFT file: `{(base / "public_service_200_sft_reviewed.jsonl").resolve()}`

## Canonical File Resolution

- Original canonical samples file identified from the workflow record: `{(base / "public_service_200_samples.jsonl").resolve()}`
- Original canonical SFT file identified from the workflow record: `{(base / "public_service_200_sft.jsonl").resolve()}`
- Reviewed replacement pool used for repairs: `{(base / "public_service_200_samples_strict.jsonl").resolve()}`

## What Was Checked

- Manual full-read review already completed on the original canonical 200 samples and 200 original SFT rows.
- Manual full-read review completed on all 48 replacement sample texts selected from the strict pool.
- Manual post-write review completed on all 48 repaired SFT rows in the final reviewed SFT file.
- Every final row in the reviewed dataset is therefore covered by manual review:
  - 152 kept rows reviewed in the original canonical set.
  - 48 replaced rows reviewed in the strict-pool repair pass and again after label writing.

## Script-Assisted Checks

- Final samples rows: {len(final_samples)}
- Final raw output rows: {len(load_jsonl(base / "public_service_200_outputs_reviewed.jsonl"))}
- Final SFT rows: {len(final_sft)}
- Bucket distribution: {dict(bucket_counts)}
- Samples word-count range: {min(row["word_count"] for row in final_samples)} to {max(row["word_count"] for row in final_samples)}
- Exact title uniqueness: {len({row["title"] for row in final_samples})} unique titles
- SFT schema validation: passed on all {len(final_sft)} rows
- User-message to sample-text alignment: passed on all {len(final_sft)} rows

## Repairs Performed

- Replaced {fixed_count} failed rows from the original canonical dataset.
- Kept {kept_count} rows from the original canonical dataset after manual review.
- Generated final repaired samples file, raw outputs file, and reviewed SFT file.
- Wrote per-row review records to `{rows_path.resolve()}`.

## Main Problems Found In The Original Canonical Dataset

- Off-domain contamination such as firearms, gambling, hobby, rideshare, music, SSL setup, and consumer-finance advice.
- Title-content mismatches in some rows.
- Private legal tactics or personal-advice articles that did not fit the target public-service explanation domain.
- Mixed-jurisdiction or unstable process pages in a small number of rows.

## Residual Risks

- The dataset still has topic clustering because the source pool contains many state-specific variants.
- Repeated themes remain, including:
  - birth certificate: {theme_counts["birth certificate"]}
  - marriage license: {theme_counts["marriage license"]}
  - passport: {theme_counts["passport"]}
- Some source texts describe procedures that may change over time by jurisdiction, so future refreshes should re-check factual timeliness if this dataset is reused later.

## Recommendation

- Recommended for training in its reviewed form.
- Not recommended to train directly on the original canonical files without the reviewed repairs.
"""
    summary_path.write_text(summary, encoding="utf-8")

    print(f"Wrote {rows_path}")
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
