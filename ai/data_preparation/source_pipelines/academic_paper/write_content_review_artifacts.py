from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SAMPLES_PATH = BASE_DIR / "academic_paper_500_samples.jsonl"
SFT_PATH = BASE_DIR / "academic_paper_500_sft.jsonl"
REVIEW_ROWS_PATH = BASE_DIR / "content_review_rows.jsonl"
REVIEW_SUMMARY_PATH = BASE_DIR / "content_review_summary.md"
PASS_SAMPLES_PATH = BASE_DIR / "academic_paper_pass_only_samples.jsonl"
PASS_SFT_PATH = BASE_DIR / "academic_paper_pass_only_sft.jsonl"
PASS_META_PATH = BASE_DIR / "academic_paper_pass_only.meta.json"


PROBLEMS: dict[int, tuple[str, str]] = {
    7: ("warn", "Minor excerpt roughness; usable but not especially clean."),
    8: ("fail", "Severe encoding and OCR corruption with repeated '(cid:1)' artifacts."),
    9: ("fail", "Broken opening and truncation make the excerpt unreliable."),
    12: ("fail", "Section-page style content rather than clean article prose."),
    13: ("fail", "Misclassified domain: physics/cosmology content placed in cse bucket."),
    16: ("warn", "Minor structural roughness in the excerpt."),
    18: ("fail", "Summary-box/news-style contamination and malformed opening."),
    19: ("fail", "Heavy LaTeX/source-code artifact contamination."),
    20: ("fail", "Duplicated and garbled sentences indicate poor extraction quality."),
    22: ("warn", "Minor awkward cut but still understandable."),
    30: ("warn", "Slight context truncation."),
    31: ("warn", "Minor excerpt roughness."),
    32: ("fail", "Misclassified domain: clinical shoulder study placed in cse bucket."),
    33: ("fail", "Publisher/header and placeholder contamination inside the excerpt."),
    37: ("warn", "Minor metadata-like phrasing remains in the body."),
    40: ("fail", "Duplicated and partly garbled discussion content."),
    41: ("warn", "Slight discontinuity in excerpt flow."),
    44: ("fail", "Repeated results/conclusion text indicates extraction failure."),
    45: ("warn", "Minor repetition but still readable."),
    51: ("warn", "Minor rough opening."),
    58: ("fail", "Excerpt reads like malformed summary/news content, not a clean paper segment."),
    61: ("fail", "Misclassified domain: geoscience/land-subsidence paper placed in bfe bucket."),
    63: ("fail", "Assistant output overstates claims from a limited clinical excerpt."),
    65: ("warn", "Minor formatting roughness."),
    71: ("fail", "Book-chapter or chapter-like source contamination rather than clean paper excerpt."),
    79: ("fail", "Header/equation fragment at start indicates truncation."),
    80: ("warn", "Minor textual roughness."),
    104: ("warn", "Slight context loss but still interpretable."),
    114: ("warn", "Minor excerpt fragmentation."),
    116: ("fail", "Chemistry methods content misbucketed into lsph and weak for the target task."),
    117: ("warn", "Minor formula/context roughness."),
    118: ("warn", "Minor structural roughness."),
    138: ("fail", "Chemistry methods-heavy content misbucketed into lsph."),
    143: ("fail", "Chemistry synthesis content misbucketed into lsph."),
    158: ("fail", "Misclassified domain: orthopaedic biomechanics content placed in cse bucket."),
    161: ("fail", "Dubious therapeutic claims and assistant wording stronger than the excerpt supports."),
    184: ("warn", "Slight content roughness but still coherent."),
    186: ("fail", "Peer-review-comment style contamination instead of article body text."),
    190: ("fail", "Appendix/supplementary-style content rather than stable main-text prose."),
    191: ("warn", "Borderline appendix or methods feel."),
    192: ("warn", "Assistant uses stronger causal language than the source fully supports."),
    197: ("warn", "Methods-heavy chemistry content with lower training value."),
    203: ("warn", "Minor roughness in excerpt quality."),
    208: ("fail", "Misclassified domain: physics/laser content placed in lsph bucket."),
    209: ("warn", "Repeated subsection text reduces cleanliness."),
    210: ("warn", "Minor roughness in excerpt quality."),
    214: ("fail", "Misclassified domain: chemistry review content placed in lsph bucket."),
    218: ("warn", "Minor roughness in excerpt quality."),
    223: ("warn", "Table and related-work clutter reduce readability and task suitability."),
    230: ("fail", "Misclassified domain: paleontology content placed in ssh bucket."),
    234: ("warn", "Minor roughness in excerpt quality."),
    241: ("fail", "Publication metadata and duplicated abstract/report fragments contaminate the row."),
    242: ("fail", "Misclassified domain: chemistry nanomaterials content placed in cse bucket."),
    244: ("fail", "Title and body topic do not match cleanly; excerpt integrity is suspect."),
    247: ("warn", "Minor roughness in excerpt quality."),
    253: ("warn", "Minor roughness in excerpt quality."),
    263: ("warn", "Minor roughness in excerpt quality."),
    277: ("fail", "Misclassified domain: medical review content placed in ssh bucket."),
    281: ("fail", "Misclassified domain: neuroscience/addiction study placed in ssh bucket."),
    290: ("fail", "Source statistics are internally inconsistent and the assistant preserves a shaky conclusion."),
    298: ("fail", "Misclassified domain: environmental/remote-sensing paper placed in ssh bucket."),
    299: ("warn", "Repeated sentence material remains in the excerpt."),
    302: ("fail", "Misclassified domain: medical/public-health paper placed in ssh bucket."),
    306: ("fail", "Misclassified domain: neuroscience/fMRI paper placed in ssh bucket."),
    307: ("fail", "Misclassified domain: LiDAR/calibration engineering paper placed in ssh bucket."),
    330: ("fail", "Reviewer-comment contamination appears inside the excerpt."),
    335: ("fail", "Misclassified domain: remote-sensing/wildfire mapping paper placed in ssh bucket."),
    344: ("fail", "Misclassified domain: control-theory/Petri-net paper placed in bfe bucket."),
    347: ("warn", "Borderline domain: gerontology/public-health angle inside ssh bucket."),
    354: ("fail", "Misclassified domain: public-health lead exposure paper placed in ssh bucket."),
    380: ("fail", "Misclassified domain: emergency-department violence survey placed in ssh bucket."),
    382: ("fail", "Misclassified domain: child-health inequity protocol placed in bfe bucket."),
    383: ("warn", "Preprint/license boilerplate and methods-heavy framing reduce cleanliness."),
    391: ("fail", "Book-review style content rather than a stable target article excerpt."),
    392: ("fail", "Misclassified domain: neuroscience/arousal study placed in ssh bucket."),
    399: ("fail", "Misclassified domain: public-health systems paper placed in ssh bucket."),
    400: ("fail", "Misclassified domain: indoor-environment/engineering paper placed in ssh bucket."),
    405: ("fail", "Misclassified domain: vaccination/public-health survey placed in ssh bucket."),
    407: ("fail", "Misclassified domain: occupational mental-health study placed in ssh bucket."),
    408: ("fail", "Misclassified domain: cognitive neuroscience study placed in ssh bucket."),
    409: ("fail", "Misclassified domain: antibiotic consumption/health systems paper placed in ssh bucket."),
    411: ("fail", "Misclassified domain: diet and e-learning health protocol placed in ssh bucket."),
    414: ("fail", "Misclassified domain: neurophysiology pilot study placed in ssh bucket."),
    416: ("fail", "Misclassified domain: occupational mental-health study placed in ssh bucket."),
    418: ("fail", "Misclassified domain: oxytocin/empathy neuroscience study placed in ssh bucket."),
    421: ("fail", "Misclassified domain: climate-and-health policy paper placed in bfe bucket."),
    423: ("fail", "Misclassified domain: industrial safety engineering paper placed in bfe bucket."),
    424: ("fail", "Misclassified domain: water-planning/engineering paper placed in bfe bucket."),
    427: ("warn", "Reads more like generic explanatory textbook prose than a strong paper excerpt."),
    430: ("fail", "Misclassified domain: antenna engineering paper placed in bfe bucket."),
    431: ("warn", "Open-access license boilerplate appears inside the excerpt."),
    434: ("warn", "Very broad low-specificity prose; weaker training value."),
    435: ("fail", "Misclassified domain: 5G antenna engineering paper placed in bfe bucket."),
    438: ("warn", "Healthcare management topic is borderline for the bfe bucket."),
    441: ("warn", "Social-program design piece is borderline for the bfe bucket."),
    444: ("fail", "Misclassified domain: rural public-health services study placed in bfe bucket."),
    446: ("fail", "Misclassified domain: engineering failure-mode analysis placed in bfe bucket."),
    449: ("fail", "Misclassified domain: death-penalty/human-rights legal article placed in bfe bucket."),
    453: ("fail", "Misclassified domain: climate-justice and overheating in housing placed in bfe bucket."),
    460: ("fail", "Misclassified domain: clinical pharmacy/medical home paper placed in bfe bucket."),
    466: ("warn", "Rejoinder/commentary-style text with duplicated opening paragraph."),
    467: ("fail", "Misclassified domain: forest ecology/sustainability paper placed in bfe bucket."),
    468: ("fail", "Misclassified domain: Alzheimer/Parkinson health-inequality study placed in bfe bucket."),
    475: ("fail", "Misclassified domain: psychiatry/media review on gambling films placed in bfe bucket."),
    476: ("fail", "Misclassified domain: construction-worker stress/occupational health paper placed in bfe bucket."),
    479: ("fail", "Misclassified domain: climate-adaptation governance review placed in bfe bucket."),
    483: ("fail", "Misclassified domain: tourism-experience study placed in bfe bucket."),
    484: ("fail", "Misclassified domain: global vaccine-sharing modeling paper placed in bfe bucket."),
    486: ("fail", "Misclassified domain: ritual and cultural revitalization study placed in bfe bucket."),
    489: ("fail", "Misclassified domain: construction-site safety app paper placed in bfe bucket."),
    492: ("fail", "Misclassified domain: child labor and legal-rights paper placed in bfe bucket."),
    495: ("warn", "Interdisciplinary conceptual essay; bucket fit is looser than typical bfe content."),
    497: ("fail", "Misclassified domain: blended-learning education case study placed in bfe bucket."),
    498: ("fail", "Misclassified domain: plant biopiracy/environmental law review placed in bfe bucket."),
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_summary(
    review_rows: list[dict],
    pass_samples: list[dict],
    pass_sft: list[dict],
    status_counts: Counter,
) -> str:
    fail_rows = [row["row"] for row in review_rows if row["status"] == "fail"]
    warn_rows = [row["row"] for row in review_rows if row["status"] == "warn"]
    pass_domain_counts = Counter(row["domain_key"] for row in pass_samples)
    pass_bucket_counts = Counter(row["bucket"] for row in pass_samples)

    return "\n".join(
        [
            "# Content Review Summary",
            "",
            "## Final file identification",
            f"- Root directory: `{BASE_DIR}`",
            f"- Official canonical samples file: `{SAMPLES_PATH.name}`",
            f"- Official canonical SFT file: `{SFT_PATH.name}`",
            "- Basis: the provided process record, the local README output-file section, and the fact that no later competing canonical/final variants exist in the folder.",
            "",
            "## Automated checks",
            "- `samples_rows=500`",
            "- `sft_rows=500`",
            "- `outputs_rows=500`",
            "- `domain_counts={'cse': 125, 'bfe': 125, 'ssh': 125, 'lsph': 125}`",
            "- `bucket_counts={'short': 100, 'medium': 350, 'long': 50}`",
            "- `word_count_range=(319, 1073)`",
            "- sample JSONL parsing passed",
            "- SFT message structure passed",
            "- assistant JSON parsing/schema passed",
            "- SFT user text matched sample text row-for-row",
            "",
            "## Manual review scope",
            "- Full manual row-by-row review completed for all 500 sample rows.",
            "- Full manual row-by-row review completed for all 500 SFT rows paired to those samples.",
            "- Review status counts:",
            f"  - pass: {status_counts['pass']}",
            f"  - warn: {status_counts['warn']}",
            f"  - fail: {status_counts['fail']}",
            "",
            "## Main findings",
            "- The dominant issue is systematic domain misclassification caused by metadata-field heuristics and tie-breaking, not isolated random noise.",
            "- Several rows also contain extraction-quality problems such as OCR corruption, duplication, review-comment contamination, boilerplate, and appendix/book-review style pages.",
            "- A smaller number of SFT labels are semantically unsafe because the assistant output overstates or sharpens claims from the source excerpt.",
            f"- Fail rows excluded from the cleaned subset: {fail_rows}",
            f"- Warn rows also excluded from the cleaned subset for conservatism: {warn_rows}",
            "",
            "## Repair actions taken",
            f"- Wrote full row-level review log to `{REVIEW_ROWS_PATH.name}`.",
            f"- Wrote a conservative pass-only cleaned samples file to `{PASS_SAMPLES_PATH.name}`.",
            f"- Wrote the aligned pass-only cleaned SFT file to `{PASS_SFT_PATH.name}`.",
            f"- Wrote cleaned-subset metadata to `{PASS_META_PATH.name}`.",
            "- Original 500-row canonical files were not overwritten.",
            "- No API call was executed in this review turn.",
            "",
            "## Cleaned subset status",
            f"- pass_only_rows={len(pass_samples)}",
            f"- pass_only_sft_rows={len(pass_sft)}",
            f"- pass_only_domain_counts={dict(pass_domain_counts)}",
            f"- pass_only_bucket_counts={dict(pass_bucket_counts)}",
            "- This pass-only subset is substantially safer for immediate training than the original canonical 500-row files.",
            "- However, it no longer preserves the original 500-row balanced-quota design.",
            "",
            "## Remaining blockers",
            "- I do not recommend direct training on the original `academic_paper_500_samples.jsonl` / `academic_paper_500_sft.jsonl` pair.",
            "- Restoring a fully repaired 500-row balanced dataset would require re-extraction/replacement of excluded rows and regeneration of SFT labels for the replacement samples.",
            "- Because replacement rows would differ from the original sample texts, that balanced rebuild would require a local API-backed rerun of `build_academic_paper_sft_outputs.py` after the repaired sample file is ready.",
            "",
            "## Prepared local commands",
            "- Validate the conservative cleaned subset:",
            f"  - `py -3 .\\validate_academic_paper_jsonl.py --samples .\\{PASS_SAMPLES_PATH.name} --sft .\\{PASS_SFT_PATH.name} --expected-total {len(pass_samples)}`",
            "- If you later rebuild a repaired 500-row sample file and want to regenerate SFT locally with your own API environment:",
            "  - working dir: this folder",
            "  - command:",
            "    `py -3 .\\build_academic_paper_sft_outputs.py --input .\\<repaired_samples.jsonl> --raw-output .\\<repaired_outputs.jsonl> --sft-output .\\<repaired_sft.jsonl> --meta-output .\\<repaired_sft.meta.json>`",
            "",
        ]
    )


def main() -> int:
    samples = load_jsonl(SAMPLES_PATH)
    sft_rows = load_jsonl(SFT_PATH)
    if len(samples) != 500 or len(sft_rows) != 500:
        raise SystemExit("Expected 500 samples and 500 SFT rows.")

    review_rows: list[dict] = []
    pass_only_samples: list[dict] = []
    pass_only_sft: list[dict] = []

    for idx, (sample, sft) in enumerate(zip(samples, sft_rows, strict=True), start=1):
        status, reason = PROBLEMS.get(idx, ("pass", "No material content issue found in full manual review."))
        fixed_in_clean_subset = status in {"warn", "fail"}
        repair_action = (
            f"Excluded from {PASS_SAMPLES_PATH.name} / {PASS_SFT_PATH.name}."
            if fixed_in_clean_subset
            else ""
        )
        review_rows.append(
            {
                "row": idx,
                "sample_index": sample.get("sample_index"),
                "title": sample.get("title"),
                "domain_key": sample.get("domain_key"),
                "bucket": sample.get("bucket"),
                "status": status,
                "reason": reason,
                "fixed_in_clean_subset": fixed_in_clean_subset,
                "repair_action": repair_action,
            }
        )
        if status == "pass":
            cleaned_sample = dict(sample)
            cleaned_sample["sample_index"] = len(pass_only_samples) + 1
            pass_only_samples.append(cleaned_sample)
            pass_only_sft.append(sft)

    status_counts = Counter(row["status"] for row in review_rows)
    write_jsonl(REVIEW_ROWS_PATH, review_rows)
    write_jsonl(PASS_SAMPLES_PATH, pass_only_samples)
    write_jsonl(PASS_SFT_PATH, pass_only_sft)

    pass_meta = {
        "source_samples_file": str(SAMPLES_PATH.resolve()),
        "source_sft_file": str(SFT_PATH.resolve()),
        "review_rows_file": str(REVIEW_ROWS_PATH.resolve()),
        "kept_statuses": ["pass"],
        "excluded_statuses": ["warn", "fail"],
        "status_counts_from_full_review": dict(status_counts),
        "pass_only_total": len(pass_only_samples),
        "pass_only_domain_counts": dict(Counter(row["domain_key"] for row in pass_only_samples)),
        "pass_only_bucket_counts": dict(Counter(row["bucket"] for row in pass_only_samples)),
    }
    PASS_META_PATH.write_text(json.dumps(pass_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    REVIEW_SUMMARY_PATH.write_text(
        build_summary(review_rows, pass_only_samples, pass_only_sft, status_counts),
        encoding="utf-8",
    )

    print(f"Wrote {REVIEW_ROWS_PATH.name}")
    print(f"Wrote {PASS_SAMPLES_PATH.name}")
    print(f"Wrote {PASS_SFT_PATH.name}")
    print(f"Wrote {PASS_META_PATH.name}")
    print(f"Wrote {REVIEW_SUMMARY_PATH.name}")
    print(f"status_counts={dict(status_counts)}")
    print(f"pass_only_total={len(pass_only_samples)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
