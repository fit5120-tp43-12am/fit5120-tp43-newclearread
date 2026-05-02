import argparse
import json
from typing import Any, Dict

from datasets import load_dataset


def safe_preview(row: Dict[str, Any], max_chars: int = 800) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, str):
            s = v.replace("\n", " ").strip()
            out[k] = s[:max_chars] + ("…" if len(s) > max_chars else "")
        elif isinstance(v, (int, float, bool)) or v is None:
            out[k] = v
        else:
            # keep structure but avoid huge dumps
            try:
                out[k] = json.loads(json.dumps(v))  # type: ignore
            except Exception:
                out[k] = str(type(v))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="common-pile/wikimedia")
    ap.add_argument("--split", default="train")
    ap.add_argument("--streaming", action="store_true", default=True)
    ap.add_argument("--limit", type=int, default=3)
    args = ap.parse_args()

    ds = load_dataset(args.dataset, split=args.split, streaming=args.streaming)
    it = iter(ds)
    first = next(it)
    print("keys:", list(first.keys()))
    def safe_print(s: str) -> None:
        # Windows consoles often default to GBK; avoid crashing on unicode bullets etc.
        print(s.encode("ascii", "backslashreplace").decode("ascii"))

    safe_print("first_row_preview:\n" + json.dumps(safe_preview(first), ensure_ascii=False, indent=2))
    n = 1
    for _ in range(args.limit - 1):
        row = next(it)
        n += 1
        safe_print(f"\nrow_{n}_preview:\n" + json.dumps(safe_preview(row), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
