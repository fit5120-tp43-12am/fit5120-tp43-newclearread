#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "build_assignment_rubric_sft_outputs.py"


def main() -> int:
    command = [
        sys.executable,
        str(SCRIPT),
        "--input",
        str(BASE / "assignment_rubric_cleaned_samples.jsonl"),
        "--raw-output",
        str(BASE / "assignment_rubric_cleaned_outputs.jsonl"),
        "--sft-output",
        str(BASE / "assignment_rubric_cleaned_sft.jsonl"),
        "--meta-output",
        str(BASE / "assignment_rubric_cleaned_sft.meta.json"),
        *sys.argv[1:],
    ]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
