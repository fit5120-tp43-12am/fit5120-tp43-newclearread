#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "extract_assignment_rubric_samples.py"


def main() -> int:
    command = [
        sys.executable,
        str(SCRIPT),
        "--output",
        str(BASE / "assignment_rubric_cleaned_samples.jsonl"),
        "--meta-output",
        str(BASE / "assignment_rubric_cleaned_samples.meta.json"),
        *sys.argv[1:],
    ]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
