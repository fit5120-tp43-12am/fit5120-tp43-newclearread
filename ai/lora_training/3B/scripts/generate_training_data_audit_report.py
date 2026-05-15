from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_DIR = ROOT / "outputs" / "data_audit" / "random_sample_100_20260513"
DEFAULT_REPORT = ROOT / "reports" / "data_audit" / "training_pair_random_audit_100_20260513.md"
DEFAULT_SUMMARY = DEFAULT_AUDIT_DIR / "audit_summary.json"
DEFAULT_REPAIR_CANDIDATES = DEFAULT_AUDIT_DIR / "minor_repair_candidates.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def mean_score(rows: list[dict[str, Any]], score_name: str) -> float | None:
    values = [row["audit"]["scores"][score_name] for row in rows if score_name in row.get("audit", {}).get("scores", {})]
    return round(statistics.mean(values), 3) if values else None


def pct(count: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{count / total * 100:.1f}%"


def markdown_counter_table(title: str, counter: Counter[str], total: int) -> str:
    lines = [f"### {title}", "", "| Category | Count | Share |", "|---|---:|---:|"]
    for key, count in counter.most_common():
        lines.append(f"| {key} | {count} | {pct(count, total)} |")
    return "\n".join(lines)


def markdown_score_table(rows: list[dict[str, Any]]) -> str:
    score_names = [
        "faithfulness",
        "coverage",
        "high_level_abstraction",
        "clarity_accessibility",
        "schema_style_fit",
        "training_value",
    ]
    lines = ["### Mean API Scores", "", "| Score dimension | Mean out of 5 |", "|---|---:|"]
    for name in score_names:
        lines.append(f"| {name.replace('_', ' ')} | {mean_score(rows, name)} |")
    return "\n".join(lines)


def markdown_group_table(rows: list[dict[str, Any]], key: str, title: str) -> str:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key))].append(row)
    lines = [f"### {title}", "", "| Group | n | Accept | Minor repair | Rewrite | Manual/drop | Mean training value |", "|---|---:|---:|---:|---:|---:|---:|"]
    for group in sorted(groups):
        group_rows = groups[group]
        decisions = Counter(row["audit"]["overall_decision"] for row in group_rows)
        lines.append(
            f"| {group} | {len(group_rows)} | {decisions.get('accept', 0)} | {decisions.get('minor_repair', 0)} | "
            f"{decisions.get('rewrite', 0)} | {decisions.get('drop_or_manual_review', 0)} | {mean_score(group_rows, 'training_value')} |"
        )
    return "\n".join(lines)


def top_problem_examples(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    priority = {"major": 0, "moderate": 1, "minor": 2, "none": 3}
    ordered = sorted(
        rows,
        key=lambda row: (
            priority.get(row["audit"].get("severity"), 9),
            row["audit"]["scores"].get("training_value", 99),
            row.get("audit_sample_id", ""),
        ),
    )
    examples = []
    for row in ordered[:limit]:
        audit = row["audit"]
        examples.append(
            {
                "audit_sample_id": row["audit_sample_id"],
                "record_id": row["record_id"],
                "domain": row.get("domain"),
                "length_bucket": row.get("natural_length_bucket"),
                "decision": audit.get("overall_decision"),
                "severity": audit.get("severity"),
                "training_value": audit.get("scores", {}).get("training_value"),
                "issue_tags": audit.get("issue_tags", []),
                "rationale": audit.get("rationale"),
            }
        )
    return examples


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate school-facing report for the 100-pair training data audit.")
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--repair-candidates", type=Path, default=DEFAULT_REPAIR_CANDIDATES)
    args = parser.parse_args()

    sample_summary = read_json(args.audit_dir / "sample_summary.json")
    api_manifest = read_json(args.audit_dir / "api_audit_manifest.json")
    rows = read_jsonl(args.audit_dir / "api_audit_outputs.jsonl")
    sample_rows = {row["audit_sample_id"]: row for row in read_jsonl(args.audit_dir / "sample_with_text.jsonl")}
    failures = read_jsonl(args.audit_dir / "api_audit_failures.jsonl")
    total = len(rows)

    decision_counts = Counter(row["audit"]["overall_decision"] for row in rows)
    severity_counts = Counter(row["audit"]["severity"] for row in rows)
    issue_counts: Counter[str] = Counter()
    for row in rows:
        issue_counts.update(row["audit"].get("issue_tags", []))
    issue_counts.pop("none", None)

    domain_counts = Counter(str(row.get("domain")) for row in rows)
    length_counts = Counter(str(row.get("natural_length_bucket")) for row in rows)
    structure_counts = Counter()
    for row in rows:
        checks = row.get("local_structure_checks") or {}
        for key, value in checks.items():
            if key == "has_markdown_fence":
                if value is True:
                    structure_counts[key] += 1
            elif value is False:
                structure_counts[key] += 1

    summary = {
        "created_at_utc": utc_now(),
        "audit_dir": str(args.audit_dir),
        "sample_summary": sample_summary,
        "api_manifest": api_manifest,
        "successful_audits": total,
        "failed_audits": len(failures),
        "decision_counts": dict(decision_counts),
        "severity_counts": dict(severity_counts),
        "domain_counts": dict(domain_counts),
        "length_counts": dict(length_counts),
        "issue_counts": dict(issue_counts),
        "structure_failure_counts": dict(structure_counts),
        "mean_scores": {
            name: mean_score(rows, name)
            for name in [
                "faithfulness",
                "coverage",
                "high_level_abstraction",
                "clarity_accessibility",
                "schema_style_fit",
                "training_value",
            ]
        },
        "top_problem_examples": top_problem_examples(rows),
        "training_data_modified": False,
    }
    write_json(args.summary, summary)

    repair_rows = []
    for row in rows:
        audit = row.get("audit", {})
        if audit.get("overall_decision") != "minor_repair":
            continue
        sample = sample_rows.get(row["audit_sample_id"], {})
        repair_rows.append(
            {
                "audit_sample_id": row["audit_sample_id"],
                "record_id": row["record_id"],
                "stable_hash": row.get("stable_hash"),
                "domain": row.get("domain"),
                "natural_length_bucket": row.get("natural_length_bucket"),
                "decision": audit.get("overall_decision"),
                "severity": audit.get("severity"),
                "issue_tags": audit.get("issue_tags", []),
                "rationale": audit.get("rationale"),
                "original_target_output_text": sample.get("target_output_text"),
                "recommended_target": audit.get("recommended_target"),
                "training_data_modified": False,
            }
        )
    write_jsonl(args.repair_candidates, repair_rows)

    accept_like = decision_counts.get("accept", 0) + decision_counts.get("minor_repair", 0)
    rewrite_like = decision_counts.get("rewrite", 0) + decision_counts.get("drop_or_manual_review", 0)

    report = f"""# Training Data Quality Audit for Small-Model Fine-Tuning

## Executive Summary

This report documents a quality audit of the supervised fine-tuning dataset used for the ClearRead summarization model. The project originally used a larger Llama 3.1 8B instruction-tuned model with LoRA fine-tuning. The next development phase aims to reduce deployment cost by moving toward a smaller model in the 3B to 4B range while preserving the same output format and a comparable level of summarization quality.

Before this audit, several model-side improvement directions were explored, including changes to training epochs, LoRA rank, learning rate, checkpoint selection, and inference prompt guards. These experiments improved understanding of the smaller-model search space, but the observed quality did not consistently reach the expected level compared with the earlier 8B baseline. This raised an important methodological question: whether the limitation came mainly from the smaller model and training setup, or whether the training targets themselves were not strong enough to teach high-level summarization.

To investigate that question, a fixed random sample of 100 training pairs was independently reviewed. The audit found that the dataset is generally strong: 90 of 100 sampled pairs were accepted as-is, 10 were marked for minor repair, and none were marked for rewrite or removal. The evidence does not support a large-scale relabeling effort before the next fine-tuning stage. Instead, the current dataset can remain the baseline for continued small-model training and parameter search.

## Project Context

The target product behavior is a compact structured summary for reading support. Given a source text of approximately 600 words, the model should return one JSON object:

```json
{{"main_idea":"two short faithful sentences","key_points":["...","...","...","..."]}}
```

The first implemented candidate used a Llama 3.1 8B instruction model with LoRA fine-tuning. Although that model provided a strong quality baseline, it also created a larger deployment footprint. The current work therefore investigates whether a smaller model, especially around the 3B scale, can provide a better practical balance between output quality, inference speed, and GPU memory usage.

The smaller-model investigation has so far included both deployment feasibility checks and training experiments. The main candidates retained for deeper work are Llama 3.2 3B Instruct, Ministral 3B, and Phi-4-mini. Earlier parameter explorations suggested that smaller models are sensitive to training setup, especially epoch count, LoRA rank, and learning rate. However, because parameter changes alone did not fully explain the quality gap, the dataset itself was audited before committing to a larger hyperparameter sweep.

## Audit Objective

The audit evaluates whether the existing supervised fine-tuning target outputs are suitable for teaching a smaller model to produce faithful, high-level, accessible summaries. It focuses on the quality of the training labels, not on model outputs.

The audit answers three questions:

1. Are the target summaries faithful to the source texts?
2. Are the summaries high-level enough for the intended two-sentence summary and four-key-point format?
3. Is there evidence that the dataset needs broad relabeling before further 3B-scale model training?

## Method

The audit used the frozen training split that had already been separated from validation and test data. No training examples were edited during this audit.

| Item | Value |
|---|---|
| Sample frame | Frozen training split only |
| Training split size | {sample_summary.get('train_record_count')} pairs |
| Sample size | {sample_summary.get('sample_size')} pairs |
| Sampling method | Fixed-seed simple random sample without replacement |
| Random seed | {sample_summary.get('sample_seed')} |
| Reviewer model | {api_manifest.get('model')} |
| Review schema | {api_manifest.get('schema_id')} |
| Training data modified | No |

Each sampled source-target pair was judged on six dimensions:

- faithfulness to the source text;
- coverage of the main message;
- high-level abstraction rather than detail copying;
- clarity and accessibility of language;
- fit with the required JSON style and schema;
- usefulness as a fine-tuning example.

The reviewer assigned one of four final decisions:

- `accept`: keep as-is.
- `minor_repair`: mostly good, but would benefit from small cleanup.
- `rewrite`: usable source text, but target label should be regenerated or substantially revised.
- `drop_or_manual_review`: possible severe problem; do not use automatically without human review.

## Dataset Coverage

{markdown_counter_table('Sample By Source Domain', domain_counts, total)}

{markdown_counter_table('Sample By Length Bucket', length_counts, total)}

## Audit Results

Out of `{total}` successfully audited training pairs:

- `{decision_counts.get('accept', 0)}` were accepted as-is.
- `{decision_counts.get('minor_repair', 0)}` were marked for minor repair.
- `{decision_counts.get('rewrite', 0)}` were marked for rewrite.
- `{decision_counts.get('drop_or_manual_review', 0)}` were marked for drop or manual review.

This means `{accept_like}` / `{total}` pairs were judged broadly usable with no or minor changes, while `{rewrite_like}` / `{total}` pairs needed substantial attention before they could be trusted as training labels.

{markdown_counter_table('Decision Counts', decision_counts, total)}

{markdown_counter_table('Severity Counts', severity_counts, total)}

{markdown_score_table(rows)}

## Issue Analysis

{markdown_counter_table('Issue Tag Counts', issue_counts, max(1, sum(issue_counts.values())))}

## Results By Domain

{markdown_group_table(rows, 'domain', 'Domain-Level Results')}

## Results By Length Bucket

{markdown_group_table(rows, 'natural_length_bucket', 'Length-Level Results')}

## Structural Checks

Before API review, each target was checked locally for parseability, key order, sentence count, key-point count, one-sentence key points, and markdown fences. These checks are weaker than semantic review, but they identify labels that may teach unstable output formatting.

Structure failure counts in the sampled set:

{markdown_counter_table('Local Structure Failure Counts', structure_counts, max(1, sum(structure_counts.values())))}

## Highest-Risk Sample Examples

The table below lists the highest-risk examples by severity and training-value score. The report does not include full source text; raw audit artifacts are stored separately for traceability.

| Sample ID | Record ID | Domain | Length | Decision | Severity | Training value | Issue tags | Rationale |
|---|---|---|---|---|---|---:|---|---|
"""
    for item in summary["top_problem_examples"]:
        tags = ", ".join(item.get("issue_tags") or [])
        rationale = str(item.get("rationale", "")).replace("|", "\\|").replace("\n", " ")
        report += (
            f"| {item['audit_sample_id']} | {item['record_id']} | {item['domain']} | {item['length_bucket']} | "
            f"{item['decision']} | {item['severity']} | {item['training_value']} | {tags} | {rationale} |\n"
        )

    report += f"""

## Interpretation

The audit results suggest that the current training labels are not the main reason smaller models have underperformed the earlier 8B baseline. The sampled labels were usually faithful, concise, high-level, and structurally aligned with the required JSON output format. The few weaknesses were minor rather than systemic.

The most common minor issues were:

- missing some rubric or requirement details in long assignment-style sources;
- losing some medical or safety nuance in health-related pages;
- including slightly too much technical detail in some academic-paper summaries;
- using a phrase that was reasonable but not directly supported by the source.

These issues are worth tracking, but they do not justify rebuilding the whole dataset. A full relabeling pass would add cost and risk without strong evidence that it would materially improve the next training stage.

## Implications For The Small-Model Search

This audit supports continuing the small-model search using the current frozen dataset. Since the labels appear broadly reliable, the next work should focus on model-side factors:

- comparing the shortlisted 3B-scale candidates under the same training and validation process;
- refining learning rate, epoch count, LoRA rank, LoRA alpha, and dropout around the strongest checkpoints;
- selecting checkpoints by validation quality before running the final frozen benchmark;
- using targeted prompt/schema guards only as inference controls, not as a substitute for training quality.

The audit also suggests that future data work should be targeted rather than broad. If later validation errors cluster around medical nuance, long rubrics, or technical academic passages, those specific groups can be audited or repaired without replacing the entire dataset.

## Recommendation

The current frozen training dataset should remain the baseline for the next round of fine-tuning experiments. No broad target-output rewrite is recommended at this stage.

A small optional repair file may be kept for the 10 sampled minor-repair cases, but those repairs should not overwrite the original dataset. Any future repaired dataset should be versioned separately, with the original source, original target, revised target, reviewer model, and repair reason recorded.

## Limitations

This audit is based on a 100-pair random sample from the training split, not a full review of all 1162 training examples. The sample includes all major source domains and length buckets, but rare dataset problems may still exist outside the sample. The review also evaluates target-label quality rather than downstream model behavior, so it should be combined with validation-set inference and benchmark scoring when selecting the final model.

## Artifacts

- Sample with source and target text: `{args.audit_dir / 'sample_with_text.jsonl'}`
- Public sample manifest without raw text: `{args.audit_dir / 'sample_manifest_public.json'}`
- API audit outputs: `{args.audit_dir / 'api_audit_outputs.jsonl'}`
- API raw requests: `{args.audit_dir / 'raw_api_requests.jsonl'}`
- API raw responses: `{args.audit_dir / 'raw_api_responses.jsonl'}`
- Machine-readable summary: `{args.summary}`
- Minor repair candidate exports: `{args.repair_candidates}`
"""

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
