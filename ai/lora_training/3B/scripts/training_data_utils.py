from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

IGNORE_INDEX = -100
EXPECTED_ROLES = ("system", "user", "assistant")


@dataclasses.dataclass(frozen=True)
class RecordMetadata:
    record_id: str
    stable_hash: str
    domain: str | None = None
    source_file: str | None = None
    source_line: int | None = None
    natural_length_bucket: str | None = None


@dataclasses.dataclass(frozen=True)
class TokenizedExampleSummary:
    index: int
    record_id: str
    stable_hash: str
    input_token_count: int
    prompt_token_count: int
    trainable_token_count: int
    mask_method: str
    was_truncated: bool
    decoded_trainable_preview: str
    decoded_trainable_json_ok: bool
    assistant_json_ok: bool
    decoded_matches_assistant_json: bool


def repo_root_from_file(file_path: str | Path) -> Path:
    return Path(file_path).resolve().parents[1]


def load_yaml_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return config


def resolve_project_path(root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(root) / path


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL row must be an object at {path}:{line_number}")
            records.append(value)
    return records


def write_text(path: str | Path, text: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")


def append_text(path: str | Path, text: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def stable_record_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest_metadata(path: str | Path) -> dict[str, RecordMetadata]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"Manifest entries must be a list: {manifest_path}")

    lookup: dict[str, RecordMetadata] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        stable_hash = str(entry.get("stable_hash", ""))
        if not stable_hash:
            continue
        lookup[stable_hash] = RecordMetadata(
            record_id=str(entry.get("record_id", stable_hash[:12])),
            stable_hash=stable_hash,
            domain=entry.get("domain"),
            source_file=entry.get("source_file"),
            source_line=entry.get("source_line"),
            natural_length_bucket=entry.get("natural_length_bucket"),
        )
    return lookup


def metadata_for_record(
    record: dict[str, Any],
    index: int,
    manifest_lookup: dict[str, RecordMetadata] | None = None,
) -> RecordMetadata:
    stable_hash = stable_record_hash(record)
    if manifest_lookup and stable_hash in manifest_lookup:
        return manifest_lookup[stable_hash]
    return RecordMetadata(record_id=f"example_{index + 1:03d}:{stable_hash[:12]}", stable_hash=stable_hash)


def validate_role_order(record: dict[str, Any], index: int | None = None) -> list[dict[str, str]]:
    label = f"record {index + 1}" if index is not None else "record"
    messages = record.get("messages")
    if not isinstance(messages, list):
        raise ValueError(f"{label} has no messages list")
    if len(messages) != 3:
        raise ValueError(f"{label} must have exactly 3 messages, found {len(messages)}")

    normalized: list[dict[str, str]] = []
    roles: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError(f"{label} contains a non-object message")
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            raise ValueError(f"{label} message role/content must be strings")
        roles.append(role)
        normalized.append({"role": role, "content": content})
    if tuple(roles) != EXPECTED_ROLES:
        raise ValueError(f"{label} roles must be {EXPECTED_ROLES}, found {tuple(roles)}")
    return normalized


def split_message_contents(messages: Sequence[dict[str, str]]) -> tuple[str, str, str]:
    return messages[0]["content"], messages[1]["content"], messages[2]["content"]


def render_chat_texts(tokenizer: Any, messages: Sequence[dict[str, str]]) -> tuple[str, str, str]:
    prompt_messages = list(messages[:2])
    full_messages = list(messages)
    prompt_text = tokenizer.apply_chat_template(
        prompt_messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    full_text = tokenizer.apply_chat_template(
        full_messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    assistant_text = messages[2]["content"]

    if not isinstance(prompt_text, str) or not isinstance(full_text, str):
        raise ValueError("Tokenizer chat template did not return text")

    if full_text.startswith(prompt_text):
        return prompt_text, full_text, assistant_text

    assistant_start = full_text.rfind(assistant_text)
    if assistant_start < 0:
        raise ValueError("Could not locate assistant content in rendered full chat text")
    prompt_from_full = full_text[:assistant_start]
    return prompt_from_full, full_text, assistant_text


def _tokenize_without_added_specials(tokenizer: Any, text: str) -> list[int]:
    encoded = tokenizer(text, add_special_tokens=False)
    ids = encoded.get("input_ids")
    if not isinstance(ids, list):
        raise ValueError("Tokenizer did not return a list of input_ids")
    return [int(token_id) for token_id in ids]


def _mask_boundary_by_offsets(tokenizer: Any, full_text: str, prompt_text: str) -> int:
    encoded = tokenizer(full_text, add_special_tokens=False, return_offsets_mapping=True)
    offsets = encoded.get("offset_mapping")
    if offsets is None:
        raise ValueError("Tokenizer cannot provide offsets for fallback prompt masking")

    prompt_chars = len(prompt_text)
    prompt_token_count = 0
    for start, end in offsets:
        if end <= prompt_chars:
            prompt_token_count += 1
            continue
        if start < prompt_chars < end:
            prompt_token_count += 1
        break
    return prompt_token_count


def create_assistant_only_features(
    tokenizer: Any,
    record: dict[str, Any],
    *,
    index: int = 0,
    max_seq_length: int | None = None,
    manifest_lookup: dict[str, RecordMetadata] | None = None,
) -> tuple[dict[str, list[int]], TokenizedExampleSummary]:
    messages = validate_role_order(record, index)
    _, _, assistant_text = split_message_contents(messages)
    prompt_text, full_text, _ = render_chat_texts(tokenizer, messages)

    prompt_ids = _tokenize_without_added_specials(tokenizer, prompt_text)
    full_ids = _tokenize_without_added_specials(tokenizer, full_text)

    mask_method = "token_prefix"
    if full_ids[: len(prompt_ids)] == prompt_ids:
        prompt_token_count = len(prompt_ids)
    else:
        prompt_token_count = _mask_boundary_by_offsets(tokenizer, full_text, prompt_text)
        mask_method = "offset_fallback"

    labels = [IGNORE_INDEX] * len(full_ids)
    for position in range(prompt_token_count, len(full_ids)):
        labels[position] = full_ids[position]

    was_truncated = False
    if max_seq_length is not None and len(full_ids) > max_seq_length:
        was_truncated = True
        full_ids = full_ids[:max_seq_length]
        labels = labels[:max_seq_length]
        prompt_token_count = min(prompt_token_count, max_seq_length)

    attention_mask = [1] * len(full_ids)
    trainable_ids = [token_id for token_id, label in zip(full_ids, labels) if label != IGNORE_INDEX]
    decoded_trainable = tokenizer.decode(trainable_ids, skip_special_tokens=True)
    decoded_trainable_json = parse_json_object(decoded_trainable)
    assistant_json = parse_json_object(assistant_text)
    metadata = metadata_for_record(record, index, manifest_lookup)

    decoded_matches_assistant = (
        decoded_trainable_json is not None
        and assistant_json is not None
        and decoded_trainable_json == assistant_json
    )

    summary = TokenizedExampleSummary(
        index=index,
        record_id=metadata.record_id,
        stable_hash=metadata.stable_hash,
        input_token_count=len(full_ids),
        prompt_token_count=prompt_token_count,
        trainable_token_count=len(trainable_ids),
        mask_method=mask_method,
        was_truncated=was_truncated,
        decoded_trainable_preview=preview_text(decoded_trainable, 220),
        decoded_trainable_json_ok=decoded_trainable_json is not None,
        assistant_json_ok=assistant_json is not None,
        decoded_matches_assistant_json=decoded_matches_assistant,
    )

    features = {
        "input_ids": full_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }
    return features, summary


def parse_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def preview_text(text: str, limit: int = 160) -> str:
    collapsed = " ".join(text.strip().split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: max(0, limit - 3)] + "..."


def ensure_tokenizer_padding(tokenizer: Any) -> None:
    if getattr(tokenizer, "pad_token", None) is None:
        eos_token = getattr(tokenizer, "eos_token", None)
        if eos_token is None:
            raise ValueError("Tokenizer has neither pad_token nor eos_token")
        tokenizer.pad_token = eos_token
    if getattr(tokenizer, "pad_token_id", None) is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id


def build_features_for_records(
    tokenizer: Any,
    records: Sequence[dict[str, Any]],
    *,
    max_seq_length: int | None,
    manifest_lookup: dict[str, RecordMetadata] | None = None,
) -> tuple[list[dict[str, list[int]]], list[TokenizedExampleSummary]]:
    features: list[dict[str, list[int]]] = []
    summaries: list[TokenizedExampleSummary] = []
    for index, record in enumerate(records):
        item_features, summary = create_assistant_only_features(
            tokenizer,
            record,
            index=index,
            max_seq_length=max_seq_length,
            manifest_lookup=manifest_lookup,
        )
        features.append(item_features)
        summaries.append(summary)
    return features, summaries


def verify_feature_summaries(summaries: Sequence[TokenizedExampleSummary]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for summary in summaries:
        prefix = f"{summary.record_id}"
        if summary.trainable_token_count <= 0:
            errors.append(f"{prefix}: no trainable assistant tokens")
        if summary.prompt_token_count <= 0:
            errors.append(f"{prefix}: no masked prompt tokens")
        if not summary.assistant_json_ok:
            errors.append(f"{prefix}: source assistant text is not valid JSON")
        if not summary.decoded_trainable_json_ok:
            errors.append(f"{prefix}: decoded trainable text is not valid JSON")
        if not summary.decoded_matches_assistant_json:
            errors.append(f"{prefix}: decoded trainable JSON does not match assistant JSON")
    return not errors, errors


def dataset_summary(records: Sequence[dict[str, Any]], metadata: Sequence[RecordMetadata]) -> dict[str, Any]:
    by_domain: dict[str, int] = {}
    by_bucket: dict[str, int] = {}
    for item in metadata:
        if item.domain:
            by_domain[item.domain] = by_domain.get(item.domain, 0) + 1
        if item.natural_length_bucket:
            by_bucket[item.natural_length_bucket] = by_bucket.get(item.natural_length_bucket, 0) + 1
    return {
        "record_count": len(records),
        "domains": dict(sorted(by_domain.items())),
        "natural_length_buckets": dict(sorted(by_bucket.items())),
    }


def format_duration(seconds: float) -> str:
    if seconds < 0 or math.isnan(seconds) or math.isinf(seconds):
        return "unknown"
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def local_timestamp(when: dt.datetime | None = None) -> str:
    value = when or dt.datetime.now().astimezone()
    return value.isoformat(timespec="seconds")


def eta_status(start_time: float, current_step: int, total_steps: int, now_time: float) -> dict[str, Any]:
    elapsed = max(0.0, now_time - start_time)
    average = elapsed / current_step if current_step > 0 else None
    remaining_steps = max(0, total_steps - current_step)
    remaining = average * remaining_steps if average is not None else None
    completion = None
    if remaining is not None:
        completion_dt = dt.datetime.now().astimezone() + dt.timedelta(seconds=remaining)
        completion = local_timestamp(completion_dt)
    return {
        "current_step": current_step,
        "total_steps": total_steps,
        "elapsed": format_duration(elapsed),
        "average_seconds_per_step": round(average, 3) if average is not None else None,
        "estimated_remaining": format_duration(remaining) if remaining is not None else "unknown",
        "estimated_completion_time": completion or "unknown",
    }


class SupervisedDataCollator:
    def __init__(self, tokenizer: Any, pad_to_multiple_of: int | None = 8) -> None:
        self.tokenizer = tokenizer
        self.pad_to_multiple_of = pad_to_multiple_of

    def __call__(self, features: Sequence[dict[str, list[int]]]) -> dict[str, Any]:
        import torch

        pad_id = self.tokenizer.pad_token_id
        if pad_id is None:
            raise ValueError("Tokenizer pad_token_id is not set")
        max_len = max(len(feature["input_ids"]) for feature in features)
        if self.pad_to_multiple_of:
            multiple = self.pad_to_multiple_of
            max_len = int(math.ceil(max_len / multiple) * multiple)

        input_ids: list[list[int]] = []
        attention_mask: list[list[int]] = []
        labels: list[list[int]] = []
        for feature in features:
            length = len(feature["input_ids"])
            pad_len = max_len - length
            input_ids.append(feature["input_ids"] + [pad_id] * pad_len)
            attention_mask.append(feature["attention_mask"] + [0] * pad_len)
            labels.append(feature["labels"] + [IGNORE_INDEX] * pad_len)

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


def markdown_table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)
