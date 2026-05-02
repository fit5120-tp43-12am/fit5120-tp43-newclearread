from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Sequence

# Keep Unsloth before any module that may import peft/transformers.
import unsloth  # noqa: F401

# Importing the validation evaluator reuses the approved deterministic metrics.
import evaluate_candidate_a_validation as ev


EXPECTED_TEST_COUNT = 145
PREDICTION_FILENAME = "test_predictions.jsonl"
METRICS_FILENAME = "test_metrics.json"
REPORT_FILENAME = "FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md"
LOG_FILENAME = "final_test_evaluation_candidate_a.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Candidate A on the final held-out test split.")
    parser.add_argument("--config", default="configs/train_llama31_8b_qlora_candidate_a.example.yaml")
    parser.add_argument("--adapter-path", default=None)
    parser.add_argument("--data-path", default="data/splits/test.jsonl")
    parser.add_argument("--manifest-path", default=None)
    parser.add_argument("--output-dir", default="outputs/evaluation/candidate_a_test")
    parser.add_argument("--expected-count", type=int, default=EXPECTED_TEST_COUNT)
    parser.add_argument(
        "--allow-heldout-test",
        action="store_true",
        help="Required guardrail acknowledging this is the approved final test evaluation.",
    )
    parser.add_argument(
        "--reuse-predictions",
        action="store_true",
        help="Rebuild metrics/report from an existing test prediction JSONL without regenerating.",
    )
    return parser.parse_args()


def write_prediction_rows(
    *,
    config: dict[str, Any],
    adapter_path: Path,
    data_path: Path,
    manifest_path: Path,
    output_path: Path,
    expected_count: int,
) -> tuple[list[dict[str, Any]], str, str, float]:
    records = ev.read_jsonl(data_path)
    if len(records) != expected_count:
        print(f"WARNING: test count {len(records)} does not match expected {expected_count}", flush=True)

    manifest_lookup = ev.load_manifest_metadata(manifest_path)
    max_new_tokens = int(config.get("inference", {}).get("max_new_tokens", 320))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model, tokenizer = ev.load_model_with_adapter(config, adapter_path)

    rows: list[dict[str, Any]] = []
    start_time = time.time()
    started_at = ev.local_timestamp()
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for index, record in enumerate(records):
            generated_text = ev.generate_candidate_a_text(
                model,
                tokenizer,
                record,
                index=index,
                max_new_tokens=max_new_tokens,
            )
            row = ev.build_prediction_row(record, index, generated_text, manifest_lookup)
            rows.append(row)
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()

            status = ev.eta_status(start_time, index + 1, len(records), time.time())
            print(
                "[{current:03d}/{total:03d}] elapsed={elapsed} avg={avg} "
                "remaining={remaining} eta={eta} domain={domain} bucket={bucket} schema={schema}".format(
                    current=index + 1,
                    total=len(records),
                    elapsed=status["elapsed"],
                    avg=status["average_seconds_per_step"],
                    remaining=status["estimated_remaining"],
                    eta=status["estimated_completion_time"],
                    domain=row.get("domain") or "unknown",
                    bucket=row.get("natural_length_bucket") or "unknown",
                    schema=row.get("schema_status"),
                ),
                flush=True,
            )

    finished_at = ev.local_timestamp()
    elapsed = time.time() - start_time
    return rows, started_at, finished_at, elapsed


def build_metrics(
    *,
    rows: Sequence[dict[str, Any]],
    config_path: Path,
    adapter_path: Path,
    data_path: Path,
    manifest_path: Path,
    output_dir: Path,
    expected_count: int,
    generation_started_at: str | None,
    generation_finished_at: str | None,
    generation_elapsed_seconds: float | None,
) -> dict[str, Any]:
    overall = ev.summarize_rows(rows)
    return {
        "created_at": ev.local_timestamp(),
        "scope": "Candidate A final held-out test split only; no training, tuning, or Candidate B.",
        "config_path": str(config_path),
        "adapter_path": str(adapter_path),
        "data_path": str(data_path),
        "split_manifest_path": str(manifest_path),
        "output_dir": str(output_dir),
        "test_count": len(rows),
        "expected_test_count": expected_count,
        "test_count_matches_expected": len(rows) == expected_count,
        "test_sha256": ev.file_sha256(data_path),
        "split_manifest_sha256": ev.file_sha256(manifest_path),
        "generation_started_at": generation_started_at,
        "generation_finished_at": generation_finished_at,
        "generation_elapsed_seconds": round(generation_elapsed_seconds, 2)
        if generation_elapsed_seconds is not None
        else None,
        "generation_elapsed": ev.format_duration(generation_elapsed_seconds or 0.0)
        if generation_elapsed_seconds is not None
        else None,
        "generation_average_seconds_per_example": round(generation_elapsed_seconds / len(rows), 3)
        if generation_elapsed_seconds and rows
        else None,
        "mojibake_patterns_scanned": ev.MOJIBAKE_PATTERNS,
        "deterministic_metrics": overall,
        "breakdowns": ev.group_breakdowns(rows),
        "mojibake_pattern_counts": {
            "predictions": ev.collect_mojibake_patterns(rows, "prediction"),
            "gold_assistant_targets": ev.collect_mojibake_patterns(rows, "gold"),
        },
        "metric_definitions": {
            "json_parse_ok": "The stripped full model output parses as a JSON object with json.loads.",
            "schema_pass": "Full output is an exact JSON object with key order main_idea, key_points; main_idea is a string; key_points is a list of exactly four strings.",
            "main_idea_two_sentences": "Approximate punctuation-based sentence count equals two.",
            "each_key_point_one_sentence": "All four key points have approximate punctuation-based sentence count equal to one.",
            "output_too_short": "Combined parsed summary text is under 35 regex words.",
            "output_too_long": "Combined parsed summary text is over 180 regex words.",
        },
    }


def row_has_deterministic_failure(row: dict[str, Any]) -> bool:
    flags = row.get("deterministic_flags", {})
    required_true = [
        "json_parse_ok",
        "schema_pass",
        "exact_key_order",
        "main_idea_string",
        "key_points_list",
        "exactly_4_key_points",
        "all_key_points_strings",
        "main_idea_two_sentences",
        "each_key_point_one_sentence",
    ]
    required_false = [
        "has_empty_string",
        "output_too_short",
        "output_too_long",
        "code_fence_or_markdown_leakage",
        "extra_text_outside_json",
        "refusal_or_meta_response",
        "prediction_mojibake",
        "gold_mojibake",
    ]
    return any(not flags.get(name) for name in required_true) or any(flags.get(name) for name in required_false)


def select_manual_review_candidates(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_hashes: set[str] = set()

    def add(row: dict[str, Any] | None) -> None:
        if row is None:
            return
        stable_hash = str(row.get("stable_hash") or "")
        if stable_hash and stable_hash in selected_hashes:
            return
        selected.append(row)
        if stable_hash:
            selected_hashes.add(stable_hash)

    by_domain: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_domain.setdefault(str(row.get("domain") or "unknown"), []).append(row)

    for row in rows:
        if row_has_deterministic_failure(row):
            add(row)

    bucket_priority = ["long", "short", "medium"]
    for domain in sorted(by_domain):
        picked = 0
        for bucket in bucket_priority:
            add(next((row for row in by_domain[domain] if row.get("natural_length_bucket") == bucket), None))
            picked = sum(1 for row in selected if row.get("domain") == domain)
            if picked >= 2:
                break
        if picked < 2:
            for row in by_domain[domain]:
                add(row)
                picked = sum(1 for item in selected if item.get("domain") == domain)
                if picked >= 2:
                    break

    focus_pairs = [
        ("medlineplus", "long"),
        ("medlineplus", "medium"),
        ("public_service", "long"),
        ("public_service", "medium"),
        ("assignment_rubric", "long"),
        ("academic_paper", "long"),
        ("academic_book", "long"),
    ]
    for domain, bucket in focus_pairs:
        add(next((row for row in rows if row.get("domain") == domain and row.get("natural_length_bucket") == bucket), None))

    for bucket in ["short", "medium", "long"]:
        add(next((row for row in rows if row.get("natural_length_bucket") == bucket), None))

    for row in rows:
        if len(selected) >= 16:
            break
        add(row)

    return selected


def build_report(metrics: dict[str, Any], rows: Sequence[dict[str, Any]]) -> str:
    overall = metrics["deterministic_metrics"]
    domain_rows = ev.breakdown_table_rows(metrics["breakdowns"]["by_domain"], "domain")
    bucket_rows = ev.breakdown_table_rows(metrics["breakdowns"]["by_natural_length_bucket"], "bucket")
    domain_bucket_rows = ev.breakdown_table_rows(metrics["breakdowns"]["by_domain_x_natural_length_bucket"], "domain_bucket")
    candidates = select_manual_review_candidates(rows)
    candidate_rows = [
        [
            row["row_index"],
            row.get("domain"),
            row.get("natural_length_bucket"),
            row.get("record_id"),
            row.get("source_file"),
            row.get("source_line"),
            row.get("schema_status"),
            ev.clean_table_cell(ev.preview_text(row.get("generated_text") or "", 120)),
        ]
        for row in candidates
    ]

    lines = [
        "# Final Test Evaluation Candidate A Report",
        "",
        f"Date/time: {metrics['created_at']}",
        "",
        "## Scope",
        "",
        "- Evaluated Candidate A on `data/splits/test.jsonl` only after central-brain approval.",
        "- Did not run training, tune parameters, change decoding settings, or run Candidate B.",
        "- Prediction JSONL and metrics JSON are local artifacts and should not be committed without central-brain approval.",
        "",
        "## Inputs And Local Artifacts",
        "",
        f"- Config: `{metrics['config_path']}`",
        f"- Adapter: `{metrics['adapter_path']}`",
        f"- Test data: `{metrics['data_path']}`",
        f"- Test SHA256: `{metrics['test_sha256']}`",
        f"- Split manifest SHA256: `{metrics['split_manifest_sha256']}`",
        f"- Test records: `{metrics['test_count']}` expected `{metrics['expected_test_count']}`",
        f"- Predictions: `{Path(metrics['output_dir']) / PREDICTION_FILENAME}`",
        f"- Metrics: `{Path(metrics['output_dir']) / METRICS_FILENAME}`",
        "",
        "## Generation Timing",
        "",
        f"- Started: `{metrics['generation_started_at']}`",
        f"- Finished: `{metrics['generation_finished_at']}`",
        f"- Elapsed: `{metrics['generation_elapsed']}`",
        f"- Average seconds/example: `{metrics['generation_average_seconds_per_example']}`",
        "",
        "## Deterministic Metrics",
        "",
        ev.markdown_table(["Metric", "Value"], ev.metric_table_rows(overall)),
        "",
        "Metric notes: sentence counts are approximate punctuation-based checks. Output too short means under 35 regex words across the parsed summary; too long means over 180 regex words.",
        "",
        "## Domain Breakdown",
        "",
        ev.markdown_table(
            [
                "Domain",
                "N",
                "JSON Parse",
                "Schema",
                "Main 2 Sent",
                "KPs 1 Sent",
                "Pred Mojibake",
                "Gold Mojibake",
                "Too Short",
                "Too Long",
            ],
            domain_rows,
        ),
        "",
        "## Natural Length Bucket Breakdown",
        "",
        ev.markdown_table(
            [
                "Bucket",
                "N",
                "JSON Parse",
                "Schema",
                "Main 2 Sent",
                "KPs 1 Sent",
                "Pred Mojibake",
                "Gold Mojibake",
                "Too Short",
                "Too Long",
            ],
            bucket_rows,
        ),
        "",
        "## Domain X Natural Length Bucket Breakdown",
        "",
        ev.markdown_table(
            [
                "Domain / Bucket",
                "N",
                "JSON Parse",
                "Schema",
                "Main 2 Sent",
                "KPs 1 Sent",
                "Pred Mojibake",
                "Gold Mojibake",
                "Too Short",
                "Too Long",
            ],
            domain_bucket_rows,
        ),
        "",
        "## Encoding And Mojibake Audit",
        "",
        f"- Patterns scanned (Unicode escaped): `{json.dumps(ev.MOJIBAKE_PATTERNS, ensure_ascii=True)}`",
        f"- Prediction mojibake rows: `{overall['counts']['prediction_mojibake_count']}`",
        f"- Gold assistant mojibake rows: `{overall['counts']['gold_mojibake_count']}`",
        f"- Prediction pattern counts: `{ev.json_dumps_ascii(metrics['mojibake_pattern_counts']['predictions'])}`",
        f"- Gold pattern counts: `{ev.json_dumps_ascii(metrics['mojibake_pattern_counts']['gold_assistant_targets'])}`",
        "",
        "## Script-Selected Manual Review Candidates",
        "",
        "The table below is the stratified candidate set selected by the script. It includes at least 2 examples from each domain where available, plus deterministic failures and required focus areas when present.",
        "",
        ev.markdown_table(
            ["Row", "Domain", "Bucket", "Record ID", "Source File", "Source Line", "Schema", "Prediction Preview"],
            candidate_rows,
        ),
        "",
        "## Manual Review",
        "",
        "Pending worker manual review.",
        "",
        "## Recommendation",
        "",
        "Pending manual review. Deterministic format metrics should be combined with stratified quality review before final-selection recommendation.",
        "",
    ]
    return "\n".join(lines)


def build_run_log(metrics: dict[str, Any]) -> str:
    overall = metrics["deterministic_metrics"]
    return "\n".join(
        [
            "# Final Test Evaluation Candidate A Log",
            "",
            f"Date/time: {metrics['created_at']}",
            "",
            "## Scope",
            "",
            "- Final held-out test split only.",
            "- No training, tuning, or Candidate B.",
            "",
            "## Inputs",
            "",
            f"- Config: `{metrics['config_path']}`",
            f"- Adapter: `{metrics['adapter_path']}`",
            f"- Data: `{metrics['data_path']}`",
            f"- Split manifest: `{metrics['split_manifest_path']}`",
            "",
            "## Outputs",
            "",
            f"- Predictions JSONL: `{Path(metrics['output_dir']) / PREDICTION_FILENAME}`",
            f"- Metrics JSON: `{Path(metrics['output_dir']) / METRICS_FILENAME}`",
            f"- Report: `reports/{REPORT_FILENAME}`",
            "",
            "## Result Summary",
            "",
            f"- Test records: `{metrics['test_count']}` expected `{metrics['expected_test_count']}`",
            f"- Test SHA256: `{metrics['test_sha256']}`",
            f"- Split manifest SHA256: `{metrics['split_manifest_sha256']}`",
            f"- Generation elapsed: `{metrics['generation_elapsed']}`",
            f"- Average seconds/example: `{metrics['generation_average_seconds_per_example']}`",
            f"- JSON parse: `{overall['rates']['json_parse_ok']['count']}/{overall['count']}`",
            f"- Schema pass: `{overall['rates']['schema_pass']['count']}/{overall['count']}`",
            f"- Main idea two sentences: `{overall['rates']['main_idea_two_sentences']['count']}/{overall['count']}`",
            f"- Each key point one sentence: `{overall['rates']['each_key_point_one_sentence']['count']}/{overall['count']}`",
            f"- Prediction mojibake rows: `{overall['counts']['prediction_mojibake_count']}`",
            f"- Gold mojibake rows: `{overall['counts']['gold_mojibake_count']}`",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = ev.resolve_project_path(root, args.config)
    config = ev.load_yaml_config(config_path)
    adapter_path = ev.resolve_project_path(root, args.adapter_path or config["outputs"]["adapter_dir"])
    data_path = ev.resolve_project_path(root, args.data_path)
    manifest_path = ev.resolve_project_path(root, args.manifest_path or config["data"]["split_manifest_path"])
    output_dir = ev.resolve_project_path(root, args.output_dir)
    prediction_path = output_dir / PREDICTION_FILENAME
    metrics_path = output_dir / METRICS_FILENAME
    report_path = root / "reports" / REPORT_FILENAME
    log_path = root / "logs" / LOG_FILENAME

    if not adapter_path.exists():
        raise FileNotFoundError(f"Adapter path does not exist: {adapter_path}")
    if data_path.name != "test.jsonl":
        raise ValueError(f"Final evaluator only allows test.jsonl, got: {data_path}")
    if not args.allow_heldout_test:
        raise ValueError("Refusing to evaluate held-out test data without --allow-heldout-test.")

    previous_metrics: dict[str, Any] | None = None
    if args.reuse_predictions and metrics_path.exists():
        previous_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    if args.reuse_predictions:
        rows = ev.refresh_prediction_rows(ev.read_prediction_rows(prediction_path), prediction_path)
        started_at = None
        finished_at = None
        elapsed = None
    else:
        rows, started_at, finished_at, elapsed = write_prediction_rows(
            config=config,
            adapter_path=adapter_path,
            data_path=data_path,
            manifest_path=manifest_path,
            output_path=prediction_path,
            expected_count=args.expected_count,
        )

    metrics = build_metrics(
        rows=rows,
        config_path=config_path,
        adapter_path=adapter_path,
        data_path=data_path,
        manifest_path=manifest_path,
        output_dir=output_dir,
        expected_count=args.expected_count,
        generation_started_at=started_at,
        generation_finished_at=finished_at,
        generation_elapsed_seconds=elapsed,
    )
    if previous_metrics is not None and elapsed is None:
        for key in (
            "generation_started_at",
            "generation_finished_at",
            "generation_elapsed_seconds",
            "generation_elapsed",
            "generation_average_seconds_per_example",
        ):
            if previous_metrics.get(key) is not None:
                metrics[key] = previous_metrics[key]

    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ev.write_text(report_path, build_report(metrics, rows))
    ev.write_text(log_path, build_run_log(metrics))

    print(
        json.dumps(
            {
                "status": "ok",
                "test_count": metrics["test_count"],
                "predictions": str(prediction_path),
                "metrics": str(metrics_path),
                "report": str(report_path),
                "log": str(log_path),
                "schema_pass": metrics["deterministic_metrics"]["rates"]["schema_pass"]["count"],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
