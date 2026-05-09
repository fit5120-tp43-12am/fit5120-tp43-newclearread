"""
Morpheme utilities (shared by the analyzer):

* ``CharVocab``                       – char-level vocabulary
* boundary <-> segment conversion     – for inference / training labels
* rule-based prefix/root/suffix tag   – ``classify_segments``
* morpheme meaning lookup             – backed by ``data/morphemes.json``
  (colingoldberg/morphemes, MIT)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

# Reserved ids must match those used at training time; the trained checkpoint
# embeds these positions and changing them would silently corrupt inference.
PAD_ID = 0
UNK_ID = 1
PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"


# --------------------------------------------------------------------------- #
# Char Vocabulary
# --------------------------------------------------------------------------- #
class CharVocab:
    """Bidirectional ``char <-> int`` mapping for the BiLSTM tagger.

    ``<pad>`` and ``<unk>`` are pre-registered at fixed ids (see ``PAD_ID`` /
    ``UNK_ID``) so the embedding layer of a loaded checkpoint stays aligned.
    Unknown characters at inference time map to ``UNK_ID`` rather than raising.
    """

    def __init__(self, char_to_id: dict[str, int] | None = None) -> None:
        if char_to_id is None:
            char_to_id = {PAD_TOKEN: PAD_ID, UNK_TOKEN: UNK_ID}
        self.char_to_id = dict(char_to_id)
        self.id_to_char = {i: c for c, i in self.char_to_id.items()}

    def __len__(self) -> int:
        return len(self.char_to_id)

    def add(self, ch: str) -> int:
        """Insert ``ch`` if absent and return its id (existing id otherwise)."""
        if ch not in self.char_to_id:
            new_id = len(self.char_to_id)
            self.char_to_id[ch] = new_id
            self.id_to_char[new_id] = ch
        return self.char_to_id[ch]

    def encode(self, word: str) -> list[int]:
        """Convert a string to its id sequence, mapping OOV chars to ``UNK_ID``."""
        return [self.char_to_id.get(ch, UNK_ID) for ch in word]

    @classmethod
    def from_words(cls, words: Iterable[str]) -> "CharVocab":
        """Build a vocab from an iterable of training words (used at train time)."""
        v = cls()
        for w in words:
            for ch in w:
                v.add(ch)
        return v

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(self.char_to_id, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "CharVocab":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data)


# --------------------------------------------------------------------------- #
# Boundary tag <-> segmentation
# --------------------------------------------------------------------------- #
def segments_to_boundary_labels(word: str, segments: list[str]) -> list[int] | None:
    """Convert a known segmentation into per-character training labels."""
    if not segments:
        return None
    joined = "".join(segments)
    if joined.lower() != word.lower():
        return None

    labels = [0] * len(word)
    cursor = 0
    for seg in segments[:-1]:
        cursor += len(seg)
        if cursor >= len(word):
            return None
        labels[cursor - 1] = 1
    return labels


def boundaries_to_segments(word: str, labels: list[int]) -> list[str]:
    """Inverse of :func:`segments_to_boundary_labels`, used at inference time."""
    segs: list[str] = []
    start = 0
    for i, ch in enumerate(word):
        if i < len(labels) and labels[i] == 1 and i < len(word) - 1:
            segs.append(word[start : i + 1])
            start = i + 1
    segs.append(word[start:])
    return [s for s in segs if s]


# --------------------------------------------------------------------------- #
# Rule-based role classifier (prefix / root / suffix)
# --------------------------------------------------------------------------- #
PREFIXES: set[str] = {
    "counter", "trans", "super", "under", "inter", "intra", "micro", "macro",
    "multi", "anti", "auto", "semi", "hyper", "hypo", "mono", "poly",
    "pseudo", "ultra", "fore", "over", "post", "para", "meta", "neo", "tele",
    "mis", "dis", "non", "pre", "pro", "sub", "ex", "un", "in", "im",
    "il", "ir", "re", "de", "co", "en", "em", "be", "ab", "ad", "com",
}

SUFFIXES: set[str] = {
    "ation", "ition", "ative", "itive", "ically", "ization", "isation",
    "tion", "sion", "ment", "ness", "ship", "hood", "ward", "wise",
    "ious", "eous", "able", "ible", "less", "ful", "ical", "ist", "ism",
    "ize", "ise", "ify", "ity", "ty", "ous", "ive", "ial", "ic",
    "al", "ish", "ly", "er", "or", "en",
    "ing", "ed", "es", "ies", "ied", "est", "s",
}


def classify_segments(segments: list[str]) -> list[dict]:
    """Assign a Prefix/Root/Suffix role to each piece produced by the tagger."""
    out: list[dict] = []
    root_anchored = False
    for i, seg in enumerate(segments):
        s = seg.lower()
        if not root_anchored and i < len(segments) - 1 and s in PREFIXES:
            out.append({"text": seg, "type": "prefix"})
        else:
            if not root_anchored:
                out.append({"text": seg, "type": "root"})
                root_anchored = True
            else:
                if s in SUFFIXES:
                    out.append({"text": seg, "type": "suffix"})
                else:
                    out.append({"text": seg, "type": "root"})
    return out


# --------------------------------------------------------------------------- #
# Morpheme meanings (data/morphemes.json at the project root)
# --------------------------------------------------------------------------- #
MEANINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "morphemes.json"


def _merge_meaning_entry(idx: dict, key: str, payload: dict) -> None:
    """Insert ``payload`` under ``key``, or merge into an existing entry."""
    key = key.lower().strip()
    if not key:
        return
    cur = idx.get(key)
    if cur is None:
        idx[key] = dict(payload)
    else:
        merged = list(
            dict.fromkeys((cur.get("meaning") or []) + (payload.get("meaning") or []))
        )
        cur["meaning"] = merged
        if not cur.get("theme") and payload.get("theme"):
            cur["theme"] = payload["theme"]
        if not cur.get("examples") and payload.get("examples"):
            cur["examples"] = payload["examples"]


def load_morpheme_meanings() -> tuple[dict, dict, dict]:
    """Build three lowercased lookup tables from ``data/morphemes.json``.

    Returns ``(prefix_index, suffix_index, root_index)``. Returns three empty
    dicts when the data file is missing, so the rest of the pipeline degrades
    gracefully instead of crashing.
    """
    if not MEANINGS_FILE.exists():
        return {}, {}, {}
    data = json.loads(MEANINGS_FILE.read_text(encoding="utf-8"))

    prefix_idx: dict[str, dict] = {}
    suffix_idx: dict[str, dict] = {}
    root_idx: dict[str, dict] = {}

    for entry in data.values():
        meaning = entry.get("meaning") or []
        theme = entry.get("theme") or ""
        examples = entry.get("examples") or []
        forms = entry.get("forms") or []
        payload = {"meaning": meaning, "theme": theme, "examples": examples}
        for f in forms:
            form = (f.get("form") or "").strip()
            loc = (f.get("loc") or "").strip().lower()
            if not form:
                continue
            if loc == "prefix":
                _merge_meaning_entry(prefix_idx, form, payload)
            elif loc == "suffix":
                _merge_meaning_entry(suffix_idx, form, payload)
            elif loc == "embedded":
                _merge_meaning_entry(root_idx, form, payload)
    return prefix_idx, suffix_idx, root_idx


_ROOT_TRIM_SUFFIXES = [
    "ation", "tion", "sion",
    "ate", "ite", "ant", "ent", "ous",
    "at", "et", "it", "ot", "ut",
    "s", "t", "e",
]

_ALLOMORPHS = [
    ("ns", "nd"),
    ("ss", "t"),
    ("ss", "d"),
    ("ct", "g"),
    ("pt", "ceive"),
]


def _root_candidates(seg: str) -> list[str]:
    """Generate root-form candidates for a segment, ordered most-specific first."""
    s = seg.lower().strip()
    seen: set[str] = set()
    out: list[str] = []

    def push(x: str) -> None:
        if x and x not in seen and len(x) >= 2:
            seen.add(x)
            out.append(x)

    push(s)
    for suf in _ROOT_TRIM_SUFFIXES:
        if s.endswith(suf) and len(s) - len(suf) >= 2:
            push(s[: -len(suf)])
    if s.endswith("e"):
        push(s[:-1])
    for a, b in _ALLOMORPHS:
        if s.endswith(a):
            push(s[: -len(a)] + b)
    return out


def lookup_meaning(
    text: str,
    role: str,
    prefix_idx: dict | None = None,
    suffix_idx: dict | None = None,
    root_idx: dict | None = None,
) -> dict | None:
    """Look up a single segment in the appropriate index."""
    if prefix_idx is None or suffix_idx is None or root_idx is None:
        prefix_idx, suffix_idx, root_idx = load_morpheme_meanings()
    key = (text or "").lower().strip()
    if not key:
        return None

    role = (role or "").lower()
    if role == "prefix" and key in prefix_idx:
        return {**prefix_idx[key], "matched": key}
    if role == "suffix" and key in suffix_idx:
        return {**suffix_idx[key], "matched": key}
    if role == "root":
        for cand in _root_candidates(key):
            if cand in root_idx:
                return {**root_idx[cand], "matched": cand}
    return None
