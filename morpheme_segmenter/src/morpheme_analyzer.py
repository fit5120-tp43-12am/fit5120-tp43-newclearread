"""
Morpheme analyzer: ONNX inference + ``MorphemeSegmenter`` class + CLI.

Wraps the trained BiLSTM boundary tagger (loaded from ONNX), the rule-based
prefix/root/suffix classifier, and the morpheme meaning dictionary. Optionally
calls WordsAPI to fetch a whole-word ``simple_meaning``, and for each
``Root`` segment optionally ``explanation`` (WordsAPI ``results[0].definition``).

CLI usage::

    python -m src.morpheme_analyzer <word> [<word> ...]

Output JSON:
    {
        "word": "...",
        "simple_meaning": "...",
        "parts": [
            {"text": "mis", "display": "mis-", "type": "Prefix",
             "meaning": ["wrong", "badly"], "matched": "..."},
            {"text": "act", "display": "act", "type": "Root",
             "meaning": null, "explanation": "something done (usually as opposed to something said)"},
            ...
        ],
        "found": true
    }

If the word cannot be meaningfully analyzed (single piece AND no dictionary
hit), only ``word`` and ``simple_meaning`` are returned.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import numpy as np
import onnxruntime as ort
import requests

from .morpheme_utils import (
    CharVocab,
    boundaries_to_segments,
    classify_segments,
    load_morpheme_meanings,
    lookup_meaning,
)

# Default artifact locations live one level above this file (the project root)
# so the package works regardless of the caller's cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_ONNX = MODELS_DIR / "morpheme_bilstm.onnx"
DEFAULT_VOCAB = MODELS_DIR / "char_vocab.json"

# Internal lowercase role -> public capitalized label exposed in the JSON.
ROLE_LABEL = {
    "prefix": "Prefix",
    "root":   "Root",
    "suffix": "Suffix",
}

# Whether to call WordsAPI to fetch a whole-word ``simple_meaning``. Requires
# RAPIDAPI_KEY (or WORDSAPI_KEY) in the environment; missing key / network
# error / non-2xx response all fall back silently to ``simple_meaning = null``.
USE_WORDSAPI = True

WORDSAPI_HOST = "wordsapiv1.p.rapidapi.com"
WORDSAPI_BASE_URL = f"https://{WORDSAPI_HOST}/words"


def _pick_wordsapi_key() -> Optional[str]:
    return os.getenv("RAPIDAPI_KEY") or os.getenv("WORDSAPI_KEY")


def _fetch_wordsapi_raw(word: str, api_key: str, *, timeout_s: float = 20) -> Dict[str, Any]:
    url = f"{WORDSAPI_BASE_URL}/{word}"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": WORDSAPI_HOST,
    }
    resp = requests.get(url, headers=headers, timeout=timeout_s)
    try:
        payload = resp.json()
    except ValueError:
        payload = {"raw": resp.text}

    if not resp.ok:
        detail = payload.get("message") or payload.get("error") or payload
        raise RuntimeError(f"WordsAPI request failed: HTTP {resp.status_code} - {detail}")

    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected WordsAPI response: not a JSON object")
    return payload


def _wordsapi_definition(data: Dict[str, Any]) -> Optional[str]:
    results = data.get("results")
    if isinstance(results, list) and results and isinstance(results[0], dict):
        d = results[0].get("definition")
        if isinstance(d, str) and d.strip():
            return d.strip()
    return None


# Process-wide memoization. Repeated calls within the same process benefit;
# also avoids hammering the API when the same word appears multiple times.
_WORD_DEF_CACHE: dict[str, str | None] = {}


def fetch_word_definition(word: str) -> str | None:
    """Best-effort lookup; returns ``None`` on any failure. Cached per process."""
    if not USE_WORDSAPI:
        return None
    key = (word or "").strip().lower()
    if not key:
        return None
    if key in _WORD_DEF_CACHE:
        return _WORD_DEF_CACHE[key]

    api_key = _pick_wordsapi_key()
    if not api_key:
        _WORD_DEF_CACHE[key] = None
        return None

    try:
        raw = _fetch_wordsapi_raw(key, api_key)
        definition = _wordsapi_definition(raw)
    except Exception:
        definition = None
    _WORD_DEF_CACHE[key] = definition
    return definition


def _format_segment(seg: str, role: str) -> str:
    if role == "Prefix":
        return f"{seg}-"
    if role == "Suffix":
        return f"-{seg}"
    return seg


class MorphemeSegmenter:
    """End-to-end morpheme analyzer backed by ONNX Runtime.

    Loads the ONNX boundary tagger plus the morpheme dictionary indices once at
    construction (the dictionary parses ~1 MB of JSON), then reuses both across
    many ``analyze`` / ``segment`` calls.

    Args:
        onnx_path:  Override the bundled ONNX model path.
        vocab_path: Override the bundled vocab path.
        threshold:  Boundary probability cut-off in ``[0, 1]``. Lower values
            produce more aggressive splitting (more, shorter pieces).
    """

    def __init__(
        self,
        onnx_path: str | Path = DEFAULT_ONNX,
        vocab_path: str | Path = DEFAULT_VOCAB,
        threshold: float = 0.5,
    ) -> None:
        onnx_path = Path(onnx_path)
        vocab_path = Path(vocab_path)
        if not onnx_path.is_file():
            raise FileNotFoundError(f"ONNX model not found.\n  expected: {onnx_path}")
        if not vocab_path.is_file():
            raise FileNotFoundError(f"Vocab not found.\n  expected: {vocab_path}")

        self.threshold = threshold
        self.vocab = CharVocab.load(vocab_path)
        self._session = ort.InferenceSession(
            str(onnx_path), providers=["CPUExecutionProvider"]
        )
        self._pref_idx, self._suff_idx, self._root_idx = load_morpheme_meanings()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def segment(self, word: str) -> list[str]:
        """Run the boundary tagger and return raw segments (no role tagging)."""
        word = word.strip()
        if not word:
            return []
        ids = np.array([self.vocab.encode(word)], dtype=np.int64)
        logits = self._session.run(None, {"ids": ids})[0]
        probs = (1.0 / (1.0 + np.exp(-np.clip(logits, -60.0, 60.0))))[0, : len(word)]
        labels = [1 if float(p) > self.threshold else 0 for p in probs]
        # A "boundary after the last char" is meaningless — force-clear it
        # in case the model ever emits a high probability there.
        labels[-1] = 0
        return boundaries_to_segments(word, labels)

    def analyze(self, word: str) -> dict:
        """Return a JSON-serializable analysis result.

        Pipeline:
            1. Optionally fetch a whole-word definition via WordsAPI.
            2. Segment with the BiLSTM tagger (ONNX Runtime).
            3. Tag each piece as Prefix / Root / Suffix.
            4. Look up each piece in the morpheme dictionary.
            5. For each Root segment, optionally attach ``explanation`` from WordsAPI.

        If the model cannot segment the word into a meaningful morphological
        structure (single piece AND no dictionary hit), only ``word`` and
        ``simple_meaning`` are returned.
        """
        simple_meaning = fetch_word_definition(word)

        segs = self.segment(word)
        items = classify_segments(segs) if segs else []

        parts: list[dict] = []
        any_meaning_hit = False
        for it in items:
            seg_text = it["text"]
            role_raw = (it.get("type") or "").lower()
            type_label = ROLE_LABEL.get(role_raw, role_raw.capitalize() or "Root")

            info = lookup_meaning(
                seg_text, role_raw, self._pref_idx, self._suff_idx, self._root_idx
            )

            meaning = info.get("meaning")[:3] if info and info.get("meaning") else None
            if meaning:
                any_meaning_hit = True

            part: dict = {
                "text": seg_text,
                "display": _format_segment(seg_text, type_label),
                "type": type_label,
                "meaning": meaning,
            }
            if info and info.get("matched") and info["matched"] != seg_text.lower():
                part["matched"] = info["matched"]
            if type_label == "Root":
                explanation = fetch_word_definition(seg_text)
                if explanation:
                    part["explanation"] = explanation
            parts.append(part)

        not_found = len(parts) <= 1 and not any_meaning_hit
        if not_found:
            return {"word": word, "simple_meaning": simple_meaning}

        return {
            "word": word,
            "simple_meaning": simple_meaning,
            "parts": parts,
            "found": True,
        }

    def analyze_json(self, word: str, *, indent: int | None = 2) -> str:
        """Convenience: return ``analyze(word)`` already JSON-serialized."""
        return json.dumps(self.analyze(word), ensure_ascii=False, indent=indent)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m src.morpheme_analyzer",
        description="Analyze morpheme segmentation of one or more words",
    )
    p.add_argument("words", nargs="+", help="One or more words to analyze")
    p.add_argument("--onnx", default=str(DEFAULT_ONNX),
                   help="Path to the ONNX model (.onnx)")
    p.add_argument("--vocab", default=str(DEFAULT_VOCAB),
                   help="Path to the char vocab JSON")
    p.add_argument("--threshold", type=float, default=0.5,
                   help="Boundary probability cut-off in [0, 1]; lower = more splits")
    return p.parse_args()


def run(words: Iterable[str], seg: MorphemeSegmenter) -> None:
    for w in words:
        print(seg.analyze_json(w))


def main() -> None:
    args = parse_args()
    try:
        seg = MorphemeSegmenter(
            onnx_path=args.onnx,
            vocab_path=args.vocab,
            threshold=args.threshold,
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    run(args.words, seg)


if __name__ == "__main__":
    main()
