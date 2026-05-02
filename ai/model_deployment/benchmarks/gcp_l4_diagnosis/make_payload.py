from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any


DEFAULT_SEED = 20020
DEFAULT_BLOCK_COUNTS = "8,9,10,12"


def parse_args() -> argparse.Namespace:
    default_dataset = Path(
        os.environ.get(
            "CLEARREAD_BENCHMARK_DATASET",
            "data/final_lora_data/outputs/accepted/all_v1.jsonl",
        )
    )
    parser = argparse.ArgumentParser(
        description=(
            "Build an in-memory benchmark payload. Raw text is written "
            "only to stdout for an SSH pipe; do not redirect stdout to a file."
        )
    )
    parser.add_argument("--dataset", type=Path, default=default_dataset)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--block-counts", default=DEFAULT_BLOCK_COUNTS)
    parser.add_argument("--synthetic-json", type=Path, default=None)
    parser.add_argument("--synthetic", action="store_true")
    return parser.parse_args()


def parse_block_counts(raw: str) -> list[int]:
    values: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            values.append(int(part))
    if not values or any(value <= 0 for value in values):
        raise ValueError("block counts must be positive")
    return values


def load_user_texts(path: Path) -> list[str]:
    texts: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number}: {exc}") from exc
            messages = record.get("messages")
            if not isinstance(messages, list):
                continue
            for message in messages:
                if not isinstance(message, dict):
                    continue
                if message.get("role") != "user":
                    continue
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    texts.append(content)
                break
    if not texts:
        raise ValueError(f"no role=user texts found in {path}")
    return texts


def load_synthetic_texts(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    blocks = payload.get("blocks")
    if not isinstance(blocks, list):
        raise ValueError("synthetic JSON must contain a blocks list")
    texts: list[str] = []
    for block in blocks:
        if isinstance(block, dict) and isinstance(block.get("text"), str):
            texts.append(block["text"])
    if not texts:
        raise ValueError(f"no synthetic block text found in {path}")
    return texts


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    block_counts = parse_block_counts(args.block_counts)
    if args.synthetic:
        if args.synthetic_json is None:
            raise ValueError("--synthetic-json is required with --synthetic")
        source_kind = "synthetic_505_word"
        texts = load_synthetic_texts(args.synthetic_json)
        selected_pool = list(texts)
    else:
        source_kind = "representative_training_style_user_text"
        texts = load_user_texts(args.dataset)
        selected_pool = list(texts)
        random.Random(args.seed).shuffle(selected_pool)

    if max(block_counts) > len(selected_pool):
        raise ValueError(
            f"largest block count {max(block_counts)} exceeds available texts {len(selected_pool)}"
        )

    batches: list[dict[str, Any]] = []
    for block_count in block_counts:
        selected = selected_pool[:block_count]
        batches.append(
            {
                "block_count": block_count,
                "seed": args.seed,
                "source_kind": source_kind,
                "texts": [
                    {"id": f"block-{index:03d}", "text": text}
                    for index, text in enumerate(selected, start=1)
                ],
            }
        )

    json.dump(
        {
            "seed": args.seed,
            "block_counts": block_counts,
            "source_kind": source_kind,
            "raw_inputs_saved": False,
            "batches": batches,
        },
        sys.stdout,
        ensure_ascii=False,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
