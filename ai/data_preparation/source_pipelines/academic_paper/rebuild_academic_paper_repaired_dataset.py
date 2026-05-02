from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from datasets import load_dataset

import extract_academic_paper_samples as base


def normalize_title_key(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z]+", " ", value.lower())).strip()


GLOBAL_EXTRA_TITLE_REJECTS = [
    re.compile(r"^[0-9]+\.\s"),
    re.compile(r"\bprotocol\b", re.IGNORECASE),
    re.compile(r"\brejoinder\b", re.IGNORECASE),
    re.compile(r"\bmini review\b", re.IGNORECASE),
    re.compile(r"\[version\s+\d+;\s*peer review", re.IGNORECASE),
]

MANUAL_REJECT_TITLE_SUBSTRINGS = {
    "ip7-spx domain interaction controls fungal virulence",
    "preparation, characterisation, and controlled release of sex pheromone-loaded mpeg-pcl diblock copolymer micelles",
    "high resolution population distribution maps for southeast asia",
    "contrasting impacts of warming and browning on periphyton",
    "distribution of optometric practices relative to deprivation index in scotland",
    "review of solutions for the use of phase change materials in geopolymers",
    "carnitine palmitoyltransferase i deficiency",
    "site-specific seismic hazard levels at the economic zone of duqm, oman",
    "the impact of folding shutter on the daylighting performance in tropical climate",
    "jiml reach mathematical connection ability by problem posing approach",
    "low-tech mall for efl intensive class among university students in remote areas",
    "post-truth politics and discursive psychology",
    "efl students pronunciation problems in presenting thesis proposal at tertiary level of english department",
    "teaching word-formation models of the lexical foundations of the german language",
    "when was silcrete heat treatment invented in south africa",
    "feminist encounters: a journal of critical studies mood, method and affect: current shifts in feminist theory",
    "the effect of quality of document service to customer satisfaction in pt. mediterranean shipping",
    "cloud based network management services",
    "green approach to the fertiliser industry: low-carbon fertilisers",
    "role of caveolae family-related proteins in the development of breast cancer",
    "steering a robotic wheelchair based on voice recognition system using convolutional neural networks",
    "current nursing education considering southern europe's reality and legal framework: a two-phased research approach",
    "global sea surface temperature and sea level rise estimation with optimal historical time lag data",
    "brentano's theory of judgment (1889): a critique of aristotle's correspondence theory of truth",
    "theory of judgment (1889): a critique of aristotle's correspondence theory of truth",
    "rethinking creativity: creative industries, ai and everyday creativity",
    "environmental impact due to incorrect waste disposal in river miriti-am",
    "strengthening aboriginal community wellbeing",
}

NORMALIZED_MANUAL_REJECT_TITLE_SUBSTRINGS = {normalize_title_key(value) for value in MANUAL_REJECT_TITLE_SUBSTRINGS}

GLOBAL_TEXT_REJECTS = [
    re.compile(r"not certified by peer review", re.IGNORECASE),
    re.compile(r"copyright holder for this preprint", re.IGNORECASE),
    re.compile(r"what is already known about this subject", re.IGNORECASE),
    re.compile(r"\bthis book\b", re.IGNORECASE),
    re.compile(r"\bin the first part of the book\b", re.IGNORECASE),
    re.compile(r"\bchapter [0-9ivxlc]+\b", re.IGNORECASE),
    re.compile(r"this is an open access article", re.IGNORECASE),
    re.compile(r"crossmark", re.IGNORECASE),
    re.compile(r"click for updates", re.IGNORECASE),
    re.compile(r"arxiv:", re.IGNORECASE),
    re.compile(r"supporting information", re.IGNORECASE),
    re.compile(r"<email_address>", re.IGNORECASE),
    re.compile(r"\\documentclass", re.IGNORECASE),
    re.compile(r"\\usepackage", re.IGNORECASE),
    re.compile(r"\bprotocol registration\b", re.IGNORECASE),
    re.compile(r"\bdesign and registration of the review\b", re.IGNORECASE),
    re.compile(r"\beligibility criteria\b", re.IGNORECASE),
    re.compile(r"\binclusion criteria\b", re.IGNORECASE),
    re.compile(r"\bexclusion criteria\b", re.IGNORECASE),
    re.compile(r"\btypes of participants\b", re.IGNORECASE),
    re.compile(r"\btypes of intervention\b", re.IGNORECASE),
    re.compile(r"\bsearch strategy\b", re.IGNORECASE),
    re.compile(r"\bdata extraction\b", re.IGNORECASE),
    re.compile(r"\bassessment of quality\b", re.IGNORECASE),
    re.compile(r"\breasons for full-text exclusion\b", re.IGNORECASE),
    re.compile(r"\brecords identified from\b", re.IGNORECASE),
    re.compile(r"\bprisma\b", re.IGNORECASE),
    re.compile(r"\bfigure\s+\d+\s*\|", re.IGNORECASE),
    re.compile(r"(?im)^figure\s+\d+\b"),
    re.compile(r"\bfrontiers in\b", re.IGNORECASE),
    re.compile(r"\barticle history\b", re.IGNORECASE),
]

MOJIBAKE_CHAR_PATTERN = re.compile(r"[鈥鈫卤螕蠂蠅蠄蟽伪碌謂掳酶锟斤拷�]")

STRICT_ALLOWED_FIELDS = {
    "cse": {"computer science", "engineering", "materials science"},
    "bfe": {"business", "economics"},
    "ssh": base.DOMAIN_FIELDS["ssh"] | {"law"},
    "lsph": base.DOMAIN_FIELDS["lsph"] | {"agricultural and food sciences"},
}

STRICT_BLOCKED_FIELDS = {
    "cse": {
        "physics",
        "mathematics",
        "chemistry",
        "geology",
        "biology",
        "medicine",
        "public health",
        "epidemiology",
        "health sciences",
        "nursing",
        "business",
        "economics",
        "law",
        "political science",
        "psychology",
        "sociology",
        "history",
        "philosophy",
        "linguistics",
        "anthropology",
        "education",
        "geography",
        "environmental science",
    },
    "bfe": {
        "physics",
        "mathematics",
        "chemistry",
        "geology",
        "biology",
        "medicine",
        "public health",
        "epidemiology",
        "health sciences",
        "nursing",
        "agricultural and food sciences",
        "environmental science",
        "computer science",
        "engineering",
        "materials science",
    },
    "ssh": {
        "physics",
        "mathematics",
        "chemistry",
        "geology",
        "biology",
        "medicine",
        "public health",
        "epidemiology",
        "health sciences",
        "nursing",
        "computer science",
        "engineering",
        "materials science",
    },
    "lsph": {
        "physics",
        "mathematics",
        "geology",
        "geography",
        "business",
        "economics",
        "law",
    },
}

UNSUPPORTED_CORE_FIELDS = {"physics", "mathematics", "chemistry", "geology"}

STRONG_LSPH_FIELDS = {
    "medicine",
    "biology",
    "public health",
    "epidemiology",
    "health sciences",
    "nursing",
    "agricultural and food sciences",
}

DOMAIN_REQUIRED_TITLE_PATTERNS = {
    "cse": re.compile(
        r"\b("
        r"algorithm|control|guidance|optimization|sensor|software|network management|wireless|antenna|"
        r"robot|robotic|robotics|signal|image|classification|segmentation|forecast|prediction|"
        r"simulation|spacecraft|orbital|petri net|photovoltaic|power system|communication|"
        r"lithography|manufacturing|embedded|circuit|device|beamforming"
        r")\b",
        re.IGNORECASE,
    ),
    "bfe": re.compile(
        r"\b("
        r"business|economics|economic|finance|financial|bank|banking|audit|firm|firms|company|companies|"
        r"customer|customers|consumer|consumers|market|marketing|insurance|supply chain|competitive advantage|"
        r"strategic planning|entrepreneur|entrepreneurship|interest rate|bankruptcy|trade|shopping|"
        r"internationalisation|board|director interlocks|e-money|risk management"
        r")\b",
        re.IGNORECASE,
    ),
    "ssh": re.compile(
        r"\b("
        r"education|teacher|teachers|student|students|learning|school|schools|political|politics|"
        r"law|legal|constitutional|history|historical|philosophy|philosophical|language|linguistic|"
        r"anthropology|anthropological|sociology|sociological|psychology|psychological|culture|cultural|"
        r"migration|identity|heritage|activists|discursive|tourism|intercultural|community|communities"
        r")\b",
        re.IGNORECASE,
    ),
    "lsph": re.compile(
        r"\b("
        r"health|medical|medicine|patient|patients|clinical|disease|diseases|virus|viral|cell|cells|"
        r"protein|proteins|cancer|epidemiology|public health|nursing|biology|biological|species|"
        r"ecology|ecological|animal|animals|plant|plants|physiology|vaccine|vaccination|infection|"
        r"tumor|tumour|genom|microbiota|metabol|radiotherapy|immune|immunology|toxicity|bacterial|"
        r"broiler|cattle|fungal|mortality|shock|screening"
        r")\b",
        re.IGNORECASE,
    ),
}

DOMAIN_POSITIVE_PATTERNS = {
    "cse": re.compile(
        r"\b("
        r"system|systems|algorithm|algorithms|network|networks|model|models|control|simulation|design|"
        r"sensor|sensors|software|computer|data|image|images|classification|machine learning|multiagent|"
        r"scada|photovoltaic|communication|communications|wireless|antenna|lidar|spectrometer|optimization|"
        r"event[- ]triggered|consensus|composite|composites|materials?|thin films?|point cloud|device|devices"
        r")\b",
        re.IGNORECASE,
    ),
    "bfe": re.compile(
        r"\b("
        r"economic|economics|finance|financial|bank|banking|accounting|audit|business|management|market|"
        r"marketing|consumer|consumers|stock|investment|investments|portfolio|firm|firms|company|companies|"
        r"corporate|entrepreneur|entrepreneurship|trade|supply chain|retail|mortgage|monetary|fiscal|tax|"
        r"taxation|unemployment|income|price|prices|sales|credit|capital inflow|foreign direct investment|"
        r"human resource|hris|personnel|talent acquisition"
        r")\b",
        re.IGNORECASE,
    ),
    "ssh": re.compile(
        r"\b("
        r"social|society|education|educational|school|teacher|teachers|student|students|learning|policy|"
        r"political|politics|history|historical|philosophy|philosophical|linguistic|language|anthropology|"
        r"anthropological|sociology|sociological|psychology|psychological|cultural|culture|media|migration|"
        r"community|communities|identity|ethnic|race|racial|children|youth|tourism|consumer decision|"
        r"public sphere|governance|ritual|tradition|literature|music|poetry"
        r")\b",
        re.IGNORECASE,
    ),
    "lsph": re.compile(
        r"\b("
        r"health|medical|medicine|patient|patients|clinical|disease|diseases|virus|viral|cell|cells|protein|"
        r"proteins|cancer|epidemiology|epidemiological|public health|nursing|biology|biological|species|"
        r"ecology|ecological|conservation|animal|animals|plant|plants|physiology|physiological|vaccine|"
        r"vaccination|infection|inflammatory|metabolite|metabolites|renal|pulmonary|stress|glucocorticoid|"
        r"biodiversity|forest|birds|lizard|women|obesity"
        r")\b",
        re.IGNORECASE,
    ),
}

DOMAIN_NEGATIVE_PATTERNS = {
    "cse": re.compile(
        r"\b("
        r"patient|patients|clinical|disease|diseases|covid|therapy|treatment|shoulder|fracture|surgery|"
        r"women|menopause|obesity|vaccine|vaccination|epidemiology|review|systematic review|protocol|"
        r"philosophy|history|political|migration|tourism|ritual|culture|child health|psychosis|depression"
        r")\b",
        re.IGNORECASE,
    ),
    "bfe": re.compile(
        r"\b("
        r"patient|patients|clinical|disease|diseases|health|medical|medicine|vaccine|vaccination|alzheimer|"
        r"parkinson|neural|neuro|brain|empathy|hospital|pharmacist|species|forest|logging|ecology|ritual|"
        r"tourism|wireless|antenna|beam|lidar|laser|blended learning|bio piracy|death penalty|construction site|"
        r"risk assessment|public health|mental disorders|child labour"
        r")\b",
        re.IGNORECASE,
    ),
    "ssh": re.compile(
        r"\b("
        r"patient|patients|clinical|disease|diseases|vaccine|vaccination|hospital|medical|medicine|protein|"
        r"metabolite|antibiotic|neural|neuro|brain|oxytocin|eeg|autonomic|pilot study|algorithm|antenna|"
        r"wireless|lidar|laser|thz|engineering|materials?|simulation of|control of|public health services"
        r")\b",
        re.IGNORECASE,
    ),
    "lsph": re.compile(
        r"\b("
        r"stock|finance|financial|bank|banking|audit|management|consumer|marketing|mortgage|fiscal|tax|"
        r"algorithm|antenna|wireless|lidar|communication network|petri net|death penalty|ritual|tourism|"
        r"music industry|brand communities"
        r")\b",
        re.IGNORECASE,
    ),
}

FIELD_NEGATIVE_HINTS = {
    "cse": {"medicine", "biology", "public health", "epidemiology", "health sciences", "nursing", "law"},
    "bfe": {"medicine", "biology", "public health", "epidemiology", "health sciences", "nursing", "computer science", "engineering", "materials science", "physics", "chemistry"},
    "ssh": {"medicine", "biology", "public health", "epidemiology", "health sciences", "nursing", "computer science", "engineering", "materials science", "physics", "chemistry"},
    "lsph": {"business", "economics", "computer science", "law"},
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Rebuild the academic-paper dataset using manual review guidance.")
    parser.add_argument("--dataset-name", default=base.DATASET_NAME)
    parser.add_argument("--dataset-split", default=base.DATASET_SPLIT)
    parser.add_argument("--base-samples", type=Path, default=base_dir / "academic_paper_500_samples.jsonl")
    parser.add_argument("--base-outputs", type=Path, default=base_dir / "academic_paper_500_outputs.jsonl")
    parser.add_argument("--review-rows", type=Path, default=base_dir / "content_review_rows.jsonl")
    parser.add_argument("--output", type=Path, default=base_dir / "academic_paper_500_repaired_samples.jsonl")
    parser.add_argument("--meta-output", type=Path, default=base_dir / "academic_paper_500_repaired_samples.meta.json")
    parser.add_argument("--seeded-raw-output", type=Path, default=base_dir / "academic_paper_500_repaired_outputs.jsonl")
    parser.add_argument("--replacements-output", type=Path, default=base_dir / "academic_paper_500_replacements_only.jsonl")
    parser.add_argument("--max-scan", type=int, default=400000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--progress-every", type=int, default=5000)
    return parser.parse_args()


def title_rejected(title: str) -> bool:
    if base.is_rejected_title(title):
        return True
    normalized = normalize_title_key(title)
    if any(needle in normalized for needle in NORMALIZED_MANUAL_REJECT_TITLE_SUBSTRINGS):
        return True
    return any(pattern.search(title) for pattern in GLOBAL_EXTRA_TITLE_REJECTS)


def text_rejected(text: str) -> bool:
    if base.excerpt_has_quality_issue(text):
        return True
    if len(MOJIBAKE_CHAR_PATTERN.findall(text)) >= 6:
        return True
    parts = re.split(r"\n\s*\n", text, maxsplit=2)
    if len(parts) >= 2:
        first_body = parts[1].lstrip()
        if first_body and first_body[0].islower():
            return True
    first_400 = text[:400]
    if re.search(r"\bdoi:\s*\S+", first_400, re.IGNORECASE):
        return True
    if re.search(r"\bdepartment of\b.*\buniversity\b", first_400, re.IGNORECASE):
        return True
    return any(pattern.search(text) for pattern in GLOBAL_TEXT_REJECTS)


def pattern_count(pattern: re.Pattern[str], text: str) -> int:
    return len(set(m.group(0).lower() for m in pattern.finditer(text)))


def field_gate(domain: str, fields: set[str], title: str, snippet: str) -> bool:
    if fields and fields.issubset(UNSUPPORTED_CORE_FIELDS):
        return False

    allowed_hits = fields & STRICT_ALLOWED_FIELDS[domain]
    blocked_hits = fields & STRICT_BLOCKED_FIELDS[domain]
    title_hits = pattern_count(DOMAIN_REQUIRED_TITLE_PATTERNS[domain], f"{title}\n{snippet}")

    if domain == "cse":
        if allowed_hits and not blocked_hits:
            return True
        if blocked_hits and title_hits < 3:
            return False
        return title_hits >= 2

    if domain == "bfe":
        if allowed_hits and not blocked_hits:
            return True
        if blocked_hits and title_hits < 3:
            return False
        return title_hits >= 2

    if domain == "ssh":
        if blocked_hits & {"medicine", "biology", "public health", "epidemiology", "health sciences", "nursing"}:
            if not (allowed_hits & {"education", "law", "political science", "history", "philosophy", "linguistics", "sociology", "anthropology"}):
                return False
        if allowed_hits and not blocked_hits:
            return True
        if blocked_hits and title_hits < 3:
            return False
        return title_hits >= 2

    if domain == "lsph":
        if fields == {"chemistry"}:
            return False
        if fields & {"geography"} and title_hits < 3:
            return False
        if allowed_hits and not blocked_hits and ((fields & STRONG_LSPH_FIELDS) or title_hits >= 2):
            return True
        if blocked_hits and title_hits < 3:
            return False
        if not (fields & STRONG_LSPH_FIELDS) and title_hits < 2:
            return False
        return title_hits >= 2

    return False


def improved_classify(title: str, body: list[str], metadata: dict[str, Any]) -> tuple[str | None, list[str], dict[str, int]]:
    fields = base.normalize_field_names(metadata.get("extfieldsofstudy")) | base.normalize_field_names(
        metadata.get("s2fieldsofstudy")
    )
    ordered = sorted(fields)
    snippet = f"{title}\n\n" + "\n\n".join(body[:2])

    scores: dict[str, int] = {}
    for domain in base.DOMAIN_FIELDS:
        if not field_gate(domain, fields, title, snippet):
            scores[domain] = -999
            continue

        field_hits = len(fields & base.DOMAIN_FIELDS[domain])
        positive_hits = pattern_count(DOMAIN_POSITIVE_PATTERNS[domain], snippet)
        negative_hits = pattern_count(DOMAIN_NEGATIVE_PATTERNS[domain], snippet)
        field_penalty = len(fields & FIELD_NEGATIVE_HINTS[domain])

        if domain == "bfe" and positive_hits == 0:
            scores[domain] = -999
            continue
        if domain == "ssh" and positive_hits == 0 and field_hits < 1:
            scores[domain] = -999
            continue
        if domain == "cse" and positive_hits == 0 and field_hits < 1:
            scores[domain] = -999
            continue
        if domain == "lsph" and positive_hits == 0 and field_hits < 1:
            scores[domain] = -999
            continue

        scores[domain] = (field_hits * 4) + (positive_hits * 2) - (negative_hits * 3) - field_penalty

    best_domain = max(scores, key=scores.get)
    best_score = scores[best_domain]
    if best_score <= 0:
        return None, ordered, scores

    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) > 1 and best_score - sorted_scores[1] < 4:
        return None, ordered, scores
    return best_domain, ordered, scores


def adjust_kept_sample(sample: dict[str, Any], new_index: int) -> dict[str, Any]:
    updated = dict(sample)
    updated["sample_index"] = new_index
    return updated


def reseed_output_row(output_row: dict[str, Any], sample_row: dict[str, Any]) -> dict[str, Any]:
    updated = dict(output_row)
    updated["sample_index"] = sample_row["sample_index"]
    updated["domain_key"] = sample_row["domain_key"]
    updated["domain_label"] = sample_row["domain_label"]
    updated["bucket"] = sample_row["bucket"]
    updated["word_count"] = sample_row["word_count"]
    updated["paper_id"] = sample_row["paper_id"]
    updated["title"] = sample_row["title"]
    updated["source_url"] = sample_row["source_url"]
    updated["source_license"] = sample_row["source_license"]
    updated["input_text"] = sample_row["text"]
    return updated


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    args = parse_args()
    rng = random.Random(args.seed)

    original_samples = load_jsonl(args.base_samples)
    original_outputs = load_jsonl(args.base_outputs)
    review_rows = load_jsonl(args.review_rows)

    original_sample_by_row = {idx + 1: row for idx, row in enumerate(original_samples)}
    original_output_by_paper_id = {str(row["paper_id"]): row for row in original_outputs}
    excluded_original_paper_ids = {str(row["paper_id"]) for row in original_samples}

    selected_rows: list[dict[str, Any]] = []
    seeded_outputs: list[dict[str, Any]] = []
    remaining = {domain: quotas.copy() for domain, quotas in base.DOMAIN_BUCKET_TARGETS.items()}

    for review in review_rows:
        row_num = int(review["row"])
        if review["status"] != "pass":
            continue
        sample = original_sample_by_row[row_num]
        adjusted = adjust_kept_sample(sample, len(selected_rows) + 1)
        selected_rows.append(adjusted)
        remaining[adjusted["domain_key"]][adjusted["bucket"]] -= 1
        seeded_outputs.append(reseed_output_row(original_output_by_paper_id[str(sample["paper_id"])], adjusted))

    replacement_rows: list[dict[str, Any]] = []
    skipped_reasons: Counter[str] = Counter()
    candidate_support: dict[str, Counter[str]] = defaultdict(Counter)
    scan_count = 0

    dataset = load_dataset(args.dataset_name, split=args.dataset_split, streaming=True)
    for row in dataset:
        if base.quotas_complete(remaining):
            break

        scan_count += 1
        if scan_count % args.progress_every == 0:
            print(f"[scan={scan_count}] selected={len(selected_rows)} replacements={len(replacement_rows)}")

        metadata = row.get("metadata") or {}
        license_name = str(metadata.get("oa_license") or "")
        if license_name not in base.ALLOWED_LICENSES:
            skipped_reasons["license"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        paper_id = str(row.get("id") or "").strip()
        if not paper_id:
            skipped_reasons["missing_id"] += 1
            if scan_count >= args.max_scan:
                break
            continue
        if paper_id in excluded_original_paper_ids:
            skipped_reasons["already_used_or_reviewed"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        raw_text = str(row.get("text") or "")
        title, body, prepare_error = base.prepare_document(raw_text)
        if prepare_error:
            skipped_reasons[prepare_error] += 1
            if scan_count >= args.max_scan:
                break
            continue
        if title_rejected(title):
            skipped_reasons["title_rejected_extra"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        domain, all_fields, domain_scores = improved_classify(title, body, metadata)
        if domain is None:
            skipped_reasons["domain_unmatched_review_guided"] += 1
            if scan_count >= args.max_scan:
                break
            continue
        if all(value == 0 for value in remaining[domain].values()):
            skipped_reasons["quota_full_for_domain"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        candidates = base.build_candidates(title, body)
        if not candidates:
            skipped_reasons["no_bucket_candidate"] += 1
            if scan_count >= args.max_scan:
                break
            continue
        for bucket in candidates:
            candidate_support[domain][bucket] += 1

        bucket = base.choose_bucket(candidates, remaining[domain], base.DOMAIN_BUCKET_TARGETS[domain], rng)
        if bucket is None:
            skipped_reasons["quota_full_for_domain_or_bucket"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        chosen = candidates[bucket]
        if text_rejected(chosen.text):
            skipped_reasons["text_rejected_extra"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        record = base.build_record(
            sample_index=len(selected_rows) + 1,
            domain=domain,
            chosen=chosen,
            row=row,
            title=title,
            all_fields=all_fields,
        )
        record["repair_source"] = "replacement_from_review_guided_rebuild"
        selected_rows.append(record)
        replacement_rows.append(record)
        excluded_original_paper_ids.add(paper_id)
        remaining[domain][bucket] -= 1
        print(
            f"[replacement {len(replacement_rows):03d}/114] {domain} | {bucket} | "
            f"{record['word_count']} words | score={domain_scores[domain]} | {title[:90]}"
        )

        if scan_count >= args.max_scan:
            break

    if not base.quotas_complete(remaining):
        raise SystemExit(f"Failed to complete quotas. Remaining={remaining}")

    write_jsonl(args.output, selected_rows)
    write_jsonl(args.seeded_raw_output, seeded_outputs)
    write_jsonl(args.replacements_output, replacement_rows)

    meta = {
        "dataset_name": args.dataset_name,
        "dataset_split": args.dataset_split,
        "base_samples_file": str(args.base_samples.resolve()),
        "base_outputs_file": str(args.base_outputs.resolve()),
        "review_rows_file": str(args.review_rows.resolve()),
        "output_file": str(args.output.resolve()),
        "seeded_raw_output_file": str(args.seeded_raw_output.resolve()),
        "replacements_output_file": str(args.replacements_output.resolve()),
        "kept_pass_rows": len(selected_rows) - len(replacement_rows),
        "replacement_rows": len(replacement_rows),
        "selected_domain_counts": dict(Counter(row["domain_key"] for row in selected_rows)),
        "selected_bucket_counts": dict(Counter(row["bucket"] for row in selected_rows)),
        "replacement_domain_counts": dict(Counter(row["domain_key"] for row in replacement_rows)),
        "replacement_bucket_counts": dict(Counter(row["bucket"] for row in replacement_rows)),
        "scan_count": scan_count,
        "remaining_after_run": remaining,
        "candidate_support": {k: dict(v) for k, v in candidate_support.items()},
        "skipped_reasons": dict(skipped_reasons),
        "seed": args.seed,
    }
    args.meta_output.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote repaired samples to {args.output}")
    print(f"Wrote seeded raw outputs to {args.seeded_raw_output}")
    print(f"Wrote replacement-only samples to {args.replacements_output}")
    print(f"Wrote metadata to {args.meta_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
