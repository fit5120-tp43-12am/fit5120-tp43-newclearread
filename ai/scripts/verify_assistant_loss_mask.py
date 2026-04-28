from __future__ import annotations

import argparse
from pathlib import Path

from transformers import AutoTokenizer

from training_data_utils import (
    build_features_for_records,
    dataset_summary,
    ensure_tokenizer_padding,
    file_sha256,
    load_manifest_metadata,
    load_yaml_config,
    local_timestamp,
    markdown_table,
    metadata_for_record,
    read_jsonl,
    resolve_project_path,
    verify_feature_summaries,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify assistant-only label masking on the smoke set.")
    parser.add_argument("--config", default="configs/smoke_llama31_8b_qlora.yaml")
    return parser.parse_args()


def load_tokenizer(model_id: str, trust_remote_code: bool):
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        use_fast=True,
        trust_remote_code=trust_remote_code,
    )
    ensure_tokenizer_padding(tokenizer)
    return tokenizer


def render_report(
    *,
    config_path: Path,
    model_id: str,
    data_path: Path,
    data_sha256: str,
    manifest_path: Path,
    summaries,
    ok: bool,
    errors: list[str],
) -> str:
    total = len(summaries)
    token_prefix_count = sum(1 for summary in summaries if summary.mask_method == "token_prefix")
    offset_count = sum(1 for summary in summaries if summary.mask_method == "offset_fallback")
    truncated_count = sum(1 for summary in summaries if summary.was_truncated)
    trainable_total = sum(summary.trainable_token_count for summary in summaries)
    prompt_total = sum(summary.prompt_token_count for summary in summaries)

    example_rows = [
        [
            summary.index + 1,
            summary.record_id,
            summary.stable_hash[:12],
            summary.prompt_token_count,
            summary.trainable_token_count,
            summary.mask_method,
            summary.decoded_trainable_json_ok,
            summary.decoded_trainable_preview.replace("|", "\\|"),
        ]
        for summary in summaries[:3]
    ]

    error_lines = ["- None"] if not errors else [f"- {error}" for error in errors]

    return "\n".join(
        [
            "# Label Mask Sanity Check",
            "",
            f"Date/time: {local_timestamp()}",
            "",
            "## Scope",
            "",
            "Verified assistant-only loss labels on the 10-record smoke set. This check loaded only the tokenizer, not full model weights.",
            "",
            "## Inputs",
            "",
            f"- Config: `{config_path.as_posix()}`",
            f"- Model tokenizer: `{model_id}`",
            f"- Smoke data: `{data_path.as_posix()}`",
            f"- Smoke data SHA256: `{data_sha256}`",
            f"- Split manifest: `{manifest_path.as_posix()}`",
            "",
            "## Result",
            "",
            f"- Overall pass: `{ok}`",
            f"- Smoke records checked: `{total}`",
            f"- Records with trainable assistant tokens: `{sum(1 for s in summaries if s.trainable_token_count > 0)}`",
            f"- Records whose decoded trainable labels parse as JSON: `{sum(1 for s in summaries if s.decoded_trainable_json_ok)}`",
            f"- Records whose decoded trainable JSON matches source assistant JSON: `{sum(1 for s in summaries if s.decoded_matches_assistant_json)}`",
            f"- Token-prefix masks: `{token_prefix_count}`",
            f"- Offset-fallback masks: `{offset_count}`",
            f"- Truncated records at configured max length: `{truncated_count}`",
            f"- Total masked prompt tokens: `{prompt_total}`",
            f"- Total trainable assistant tokens: `{trainable_total}`",
            "",
            "## Example Label Summaries",
            "",
            markdown_table(
                [
                    "#",
                    "Record ID",
                    "Stable Hash",
                    "Prompt Tokens",
                    "Trainable Tokens",
                    "Mask Method",
                    "Trainable JSON OK",
                    "Decoded Trainable Preview",
                ],
                example_rows,
            ),
            "",
            "## Errors",
            "",
            "\n".join(error_lines),
            "",
            "## Interpretation",
            "",
            "The prompt region contains the system and user/source text plus the assistant generation header. Labels for that region are set to `-100`, so loss is computed only on the assistant JSON completion tokens.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = resolve_project_path(root, args.config)
    config = load_yaml_config(config_path)

    model_id = config["model"]["base_model_id"]
    trust_remote_code = bool(config["model"].get("trust_remote_code", True))
    data_path = resolve_project_path(root, config["data"]["smoke_path"])
    manifest_path = resolve_project_path(root, config["data"]["split_manifest_path"])
    report_path = resolve_project_path(root, config["outputs"]["mask_report_path"])
    max_seq_length = int(config["data"]["max_seq_length"])

    records = read_jsonl(data_path)
    manifest_lookup = load_manifest_metadata(manifest_path)
    metadata = [metadata_for_record(record, index, manifest_lookup) for index, record in enumerate(records)]
    tokenizer = load_tokenizer(model_id, trust_remote_code)
    _, summaries = build_features_for_records(
        tokenizer,
        records,
        max_seq_length=max_seq_length,
        manifest_lookup=manifest_lookup,
    )
    ok, errors = verify_feature_summaries(summaries)
    if len(records) != 10:
        ok = False
        errors.append(f"Expected 10 smoke records, found {len(records)}")

    summary = dataset_summary(records, metadata)
    report = render_report(
        config_path=config_path,
        model_id=model_id,
        data_path=data_path,
        data_sha256=file_sha256(data_path),
        manifest_path=manifest_path,
        summaries=summaries,
        ok=ok,
        errors=errors,
    )
    write_text(report_path, report)

    print(
        {
            "status": "pass" if ok else "fail",
            "records": len(records),
            "domains": summary["domains"],
            "mask_report": str(report_path),
            "trainable_tokens": sum(item.trainable_token_count for item in summaries),
        }
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
