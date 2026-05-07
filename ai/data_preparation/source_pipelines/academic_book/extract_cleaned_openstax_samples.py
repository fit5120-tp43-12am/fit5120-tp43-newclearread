import argparse
import hashlib
import json
import os
import random
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from datasets import load_dataset
from huggingface_hub import HfApi


HERE = os.path.dirname(os.path.abspath(__file__))


CNX_URL_RE = re.compile(r"https?://cnx\.org/content/(col\d+/\d+\.\d+)", re.I)
URL_RE = re.compile(r"https?://\S+", re.I)
SPACED_CAPS_RE = re.compile(r"(?:\b[A-Z]\b(?:\s+|$)){4,}")
MATH_SYMBOL_RE = re.compile(r"[=<>^∫√πΣΔ±÷×/\\]")
OPTION_MARKER_RE = re.compile(r"\b[a-d]\.\s", re.I)
SECOND_PERSON_RE = re.compile(r"\b(?:you|your|yourself|you're|you've|you'll)\b", re.I)


BUCKET_CONFIG = {
    "short": (250, 499, 350),
    "medium": (500, 800, 700),
    "long": (801, 1200, 1000),
}


HARD_LINE_PATTERNS = [
    re.compile(r"^\s*this openstax book is available for free at\b", re.I),
    re.compile(r"^\s*chapter\s+\d+\s*\|", re.I),
    re.compile(r"^\s*figure\s+\d+", re.I),
    re.compile(r"^\s*table\s+\d+", re.I),
    re.compile(r"\bcredit:\b", re.I),
    re.compile(r"\bopenstaxcollege\.org/l/\b", re.I),
    re.compile(r"\bopenstax\.org/l/\b", re.I),
]


HARD_SENTENCE_PATTERNS = [
    re.compile(r"\blearning objective\b", re.I),
    re.compile(r"\blearning objectives\b", re.I),
    re.compile(r"\bchapter objectives\b", re.I),
    re.compile(r"\bby the end of this section\b", re.I),
    re.compile(r"\bafter studying this chapter\b", re.I),
    re.compile(r"\bappendix\b", re.I),
    re.compile(r"\bprofessor\b", re.I),
    re.compile(r"\bstudy group\b", re.I),
    re.compile(r"\bexam\b", re.I),
    re.compile(r"\bcalculator\b", re.I),
    re.compile(r"\bexcel\b", re.I),
    re.compile(r"\blinregttest\b", re.I),
    re.compile(r"\binput screen\b", re.I),
    re.compile(r"\bclick ok\b", re.I),
    re.compile(r"\bbig idea\b", re.I),
    re.compile(r"\benduring understanding\b", re.I),
    re.compile(r"\bessential knowledge\b", re.I),
    re.compile(r"\bscience practice\b", re.I),
    re.compile(r"\bap(?:®)?\b", re.I),
    re.compile(r"\bthe science practice challenge questions\b", re.I),
    re.compile(r"\btable of contents\b", re.I),
    re.compile(r"\bkey terms\b", re.I),
    re.compile(r"\bchapter summary\b", re.I),
    re.compile(r"\breview questions\b", re.I),
    re.compile(r"\bproblems?\s*(?:&|and)\s*exercises\b", re.I),
    re.compile(r"\bself-check\b", re.I),
    re.compile(r"\bcheck your learning\b", re.I),
    re.compile(r"\bwhat would you do\?\b", re.I),
    re.compile(r"\bwhat can you do\?\b", re.I),
    re.compile(r"\bwhy it matters\b", re.I),
    re.compile(r"\byour turn\b", re.I),
    re.compile(r"\blink to learning\b", re.I),
    re.compile(r"\bphet explorations?\b", re.I),
    re.compile(r"\bclear it up\b", re.I),
    re.compile(r"\bwork it out\b", re.I),
    re.compile(r"\bstudent survey\b", re.I),
    re.compile(r"\bstudy strategies?\b", re.I),
    re.compile(r"\binterleaving\b", re.I),
    re.compile(r"\bspacing\b", re.I),
    re.compile(r"\babout this chapter\b", re.I),
    re.compile(r"\babout openstax\b", re.I),
    re.compile(r"\bopenstax is a nonprofit\b", re.I),
    re.compile(r"\bopenstax tutor\b", re.I),
    re.compile(r"\bthis textbook was written to increase student access\b", re.I),
    re.compile(r"\berrata\b", re.I),
    re.compile(r"\bpreface\b", re.I),
    re.compile(r"\babout the authors\b", re.I),
    re.compile(r"\bcontributing authors\b", re.I),
    re.compile(r"\bsolutions? manual\b", re.I),
    re.compile(r"\btry it\b", re.I),
    re.compile(r"\bsolution\b", re.I),
    re.compile(r"\bproblem-solving strategy\b", re.I),
    re.compile(r"\bexample\s+\d", re.I),
    re.compile(r"\btheorem\s+\d", re.I),
    re.compile(r"\bproof\b", re.I),
    re.compile(r"\bwatch this video\b", re.I),
    re.compile(r"\bvisit this website\b", re.I),
    re.compile(r"\binteractive planning technology\b", re.I),
    re.compile(r"\bdegree audit\b", re.I),
    re.compile(r"\bcredit\b", re.I),
    re.compile(r"\bwikimedia commons\b", re.I),
    re.compile(r"\bseries or test conclusions\b", re.I),
    re.compile(r"\banswers? will vary\b", re.I),
    re.compile(r"\bmanagerial leadership\b", re.I),
    re.compile(r"\bethical considerations\b", re.I),
    re.compile(r"\bcatching the entrepreneurial spirit\b", re.I),
    re.compile(r"\bentrepreneur in action\b", re.I),
    re.compile(r"\bastronomy and mythology\b", re.I),
    re.compile(r"\bhow not to lie with statistics\b", re.I),
    re.compile(r"\ba few words about the real world\b", re.I),
    re.compile(r"\bglossary\b", re.I),
    re.compile(r"\bactivity\b", re.I),
    re.compile(r"\bthink about it\b", re.I),
    re.compile(r"\bsection summary\b", re.I),
    re.compile(r"\bstrategy\b", re.I),
    re.compile(r"\bdiscussion\b", re.I),
    re.compile(r"\bgeneticist\b", re.I),
    re.compile(r"\btransferable skills\b", re.I),
    re.compile(r"\bpreprofessional\b", re.I),
    re.compile(r"\bcollege career\b", re.I),
    re.compile(r"\bwhat to do to get ready\b", re.I),
    re.compile(r"\bksas?\b", re.I),
    re.compile(r"\bresume(?:s)?\b", re.I),
    re.compile(r"\bcover letter\b", re.I),
    re.compile(r"\bpitch competitions?\b", re.I),
    re.compile(r"\bpitch deck\b", re.I),
    re.compile(r"\bbrief business plan\b", re.I),
    re.compile(r"\btypes of business plans\b", re.I),
    re.compile(r"\bexecutive summary\b", re.I),
    re.compile(r"\binternship\b", re.I),
    re.compile(r"\br(?:e|é)sum(?:e|é)\b", re.I),
    re.compile(r"\bjob interview\b", re.I),
    re.compile(r"\bcustomer-led pricing\b", re.I),
    re.compile(r"\bloss leader pricing\b", re.I),
    re.compile(r"\blean startup\b", re.I),
    re.compile(r"\bcustomer discovery\b", re.I),
    re.compile(r"\bcustomer validation\b", re.I),
    re.compile(r"\bray tracing\b", re.I),
    re.compile(r"\bimage formation by thin lenses\b", re.I),
    re.compile(r"\bthings great and small\b", re.I),
    re.compile(r"\busing paper, pencil, and a straight edge\b", re.I),
    re.compile(r"\busing inexpensive and common household items\b", re.I),
    re.compile(r"\bcreate a model\b", re.I),
    re.compile(r"\bstudents who want to pursue careers?\b", re.I),
    re.compile(r"\bfind employment in\b", re.I),
    re.compile(r"\bcareer of the\b", re.I),
    re.compile(r"\bto prepare for a [a-z-]+ career\b", re.I),
    re.compile(r"\byour goal should be\b", re.I),
    re.compile(r"\bbefore moving on, you need to review\b", re.I),
    re.compile(r"\byou have already learned\b", re.I),
    re.compile(r"\byou have probably seen\b", re.I),
    re.compile(r"\byou need to consume\b", re.I),
    re.compile(r"\btaking into consideration that\b", re.I),
    re.compile(r"\bbushels per acre\b", re.I),
    re.compile(r"\blimited survival\b", re.I),
    re.compile(r">\s*\d+\s+fatal\b", re.I),
    re.compile(r"\bthereby obliterating responsible microorganisms\b", re.I),
    re.compile(r"\bfunctional group structural formula importance\b", re.I),
    re.compile(r"\bdominant traits\b.*\brecessive traits\b", re.I),
    re.compile(r"\bneurotransmitter example location\b", re.I),
    re.compile(r"\borgan location function\b", re.I),
    re.compile(r"\bfactors results\b", re.I),
    re.compile(r"\bfemale reproductive anatomy\b", re.I),
    re.compile(r"\bfield biologist\b", re.I),
    re.compile(r"\brespiratory therapist\b", re.I),
    re.compile(r"\black nucleus\b", re.I),
    re.compile(r"\bcontain nucleus\b", re.I),
    re.compile(r"\bstructural formula\b", re.I),
    re.compile(r"\bspss\b", re.I),
    re.compile(r"\bopening statements? of plaintiff and defendant\b", re.I),
    re.compile(r"\bsteps? of mediation\b", re.I),
    re.compile(r"^\s*step\s+\d+\s*:", re.I),
    re.compile(r"^\s*what to do to get ready\b", re.I),
    re.compile(r"^\s*perform tests? of\b", re.I),
    re.compile(r"\bexercise\s+[a-z]?\d+\b", re.I),
]


SOFT_WINDOW_PATTERNS = [
    re.compile(r"\bfigure\s+\d", re.I),
    re.compile(r"\btable\s+\d", re.I),
    re.compile(r"\bfigure\s+[A-Z]?\d+\b", re.I),
    re.compile(r"\btable\s+[A-Z]?\d+\b", re.I),
    re.compile(r"\bexercise\s+[A-Z]?\d+\b", re.I),
    re.compile(r"\bexhibit\s+\d", re.I),
    re.compile(r"\bcredit:\b", re.I),
    re.compile(r"\bchapter\s+\d+\b", re.I),
    re.compile(r"\bcopyright\b|©|\xa9", re.I),
    re.compile(r"\bfor the following exercises\b", re.I),
    re.compile(r"\babout openstax\b", re.I),
    re.compile(r"\berrata\b", re.I),
    re.compile(r"\bopenstax tutor\b", re.I),
    re.compile(r"\bopenstax\b", re.I),
    re.compile(r"\bglossary\b", re.I),
    re.compile(r"\bkey concepts and summary\b", re.I),
    re.compile(r"\banswers? will vary\b", re.I),
    re.compile(r"\bactivity\b", re.I),
    re.compile(r"\bthink about it\b", re.I),
    re.compile(r"\bsection summary\b", re.I),
    re.compile(r"\bstrategy\b", re.I),
    re.compile(r"\bdiscussion\b", re.I),
    re.compile(r"\bresume(?:s)?\b", re.I),
    re.compile(r"\bksas?\b", re.I),
    re.compile(r"\bpreprofessional\b", re.I),
    re.compile(r"\blean startup\b", re.I),
    re.compile(r"\bcustomer discovery\b", re.I),
    re.compile(r"\bmanagerial leadership\b", re.I),
    re.compile(r"\bethical considerations\b", re.I),
    re.compile(r"\bcatching the entrepreneurial spirit\b", re.I),
    re.compile(r"\(\s*[a-d]\s*\)", re.I),
    re.compile(r"\bin\s+\([a-d]\)", re.I),
    re.compile(r"\b\d+(?:\.\d+)+\s+[A-Z]", re.I),
    re.compile(r"\b\d{3,4}\s+[A-Z][a-z]+", re.I),
    re.compile(r"\u2022"),
]


SOFT_SENTENCE_PATTERNS = [
    re.compile(r"\bfigure\s+[A-Z]?\d+\b", re.I),
    re.compile(r"\btable\s+[A-Z]?\d+\b", re.I),
    re.compile(r"\bexercise\s+[A-Z]?\d+\b", re.I),
    re.compile(r"\bexhibit\s+\d", re.I),
    re.compile(r"\bchapter\s+\d+\b", re.I),
    re.compile(r"\bglossary\b", re.I),
    re.compile(r"\bkey concepts and summary\b", re.I),
    re.compile(r"\banswers? will vary\b", re.I),
    re.compile(r"\bactivity\b", re.I),
    re.compile(r"\bthink about it\b", re.I),
    re.compile(r"\bsection summary\b", re.I),
    re.compile(r"\bstrategy\b", re.I),
    re.compile(r"\bdiscussion\b", re.I),
    re.compile(r"\bmanagerial leadership\b", re.I),
    re.compile(r"\bethical considerations\b", re.I),
    re.compile(r"\bcatching the entrepreneurial spirit\b", re.I),
    re.compile(r"\bresume(?:s)?\b", re.I),
    re.compile(r"\bksas?\b", re.I),
    re.compile(r"\bpreprofessional\b", re.I),
    re.compile(r"\blean startup\b", re.I),
    re.compile(r"\bcustomer discovery\b", re.I),
    re.compile(r"\bcustomer validation\b", re.I),
    re.compile(r"\bshown on the left\b", re.I),
    re.compile(r"\bthe figure shows\b", re.I),
    re.compile(r"\bthe figure displays\b", re.I),
    re.compile(r"\bsee also the photograph\b", re.I),
    re.compile(r"\bthe size of the page\b", re.I),
    re.compile(r"\bopenstax\b", re.I),
    re.compile(r"\u2022"),
]


MODULE_BAD_PATTERNS = [
    re.compile(r"\blearning objective\b", re.I),
    re.compile(r"\blearning objectives\b", re.I),
    re.compile(r"\bchapter objectives\b", re.I),
    re.compile(r"\bby the end of this section\b", re.I),
    re.compile(r"\bafter studying this chapter\b", re.I),
    re.compile(r"\bappendix\b", re.I),
    re.compile(r"\bprofessor\b", re.I),
    re.compile(r"\bstudy group\b", re.I),
    re.compile(r"\bexam\b", re.I),
    re.compile(r"\bcalculator\b", re.I),
    re.compile(r"\bexcel\b", re.I),
    re.compile(r"\blinregttest\b", re.I),
    re.compile(r"\binput screen\b", re.I),
    re.compile(r"\bclick ok\b", re.I),
    re.compile(r"\bbig idea\b", re.I),
    re.compile(r"\bscience practice\b", re.I),
    re.compile(r"\bap(?:®)?\b", re.I),
    re.compile(r"\btable of contents\b", re.I),
    re.compile(r"\bkey terms\b", re.I),
    re.compile(r"\bchapter summary\b", re.I),
    re.compile(r"\bwhat can you do\?\b", re.I),
    re.compile(r"\bwhy it matters\b", re.I),
    re.compile(r"\bwork it out\b", re.I),
    re.compile(r"\byour turn\b", re.I),
    re.compile(r"\bstudent survey\b", re.I),
    re.compile(r"\bstudy strategies?\b", re.I),
    re.compile(r"\binterleaving\b", re.I),
    re.compile(r"\bactivity\b", re.I),
    re.compile(r"\bthink about it\b", re.I),
    re.compile(r"\bsection summary\b", re.I),
    re.compile(r"\bstrategy\b", re.I),
    re.compile(r"\bdiscussion\b", re.I),
    re.compile(r"\bgeneticist\b", re.I),
    re.compile(r"\btransferable skills\b", re.I),
    re.compile(r"\bpreprofessional\b", re.I),
    re.compile(r"\bcollege career\b", re.I),
    re.compile(r"\bwhat to do to get ready\b", re.I),
    re.compile(r"\bksas?\b", re.I),
    re.compile(r"\bresume(?:s)?\b", re.I),
    re.compile(r"\bcover letter\b", re.I),
    re.compile(r"\bpitch deck\b", re.I),
    re.compile(r"\bbrief business plan\b", re.I),
    re.compile(r"\btypes of business plans\b", re.I),
    re.compile(r"\bexecutive summary\b", re.I),
    re.compile(r"\binternship\b", re.I),
    re.compile(r"\br(?:e|é)sum(?:e|é)\b", re.I),
    re.compile(r"\bjob interview\b", re.I),
    re.compile(r"\blean startup\b", re.I),
    re.compile(r"\bcustomer discovery\b", re.I),
    re.compile(r"\bcustomer validation\b", re.I),
    re.compile(r"\bray tracing\b", re.I),
    re.compile(r"\bimage formation by thin lenses\b", re.I),
    re.compile(r"\busing paper, pencil, and a straight edge\b", re.I),
    re.compile(r"\busing inexpensive and common household items\b", re.I),
    re.compile(r"\bcreate a model\b", re.I),
    re.compile(r"\bstudents who want to pursue careers?\b", re.I),
    re.compile(r"\bfind employment in\b", re.I),
    re.compile(r"\bcareer of the\b", re.I),
    re.compile(r"\bto prepare for a [a-z-]+ career\b", re.I),
    re.compile(r"\byour goal should be\b", re.I),
    re.compile(r"\bbefore moving on, you need to review\b", re.I),
    re.compile(r"\byou have already learned\b", re.I),
    re.compile(r"\byou have probably seen\b", re.I),
    re.compile(r"\byou need to consume\b", re.I),
    re.compile(r"\bfunctional group structural formula importance\b", re.I),
    re.compile(r"\bdominant traits\b.*\brecessive traits\b", re.I),
    re.compile(r"\bneurotransmitter example location\b", re.I),
    re.compile(r"\borgan location function\b", re.I),
    re.compile(r"\bfactors results\b", re.I),
    re.compile(r"\bfemale reproductive anatomy\b", re.I),
    re.compile(r"\bfield biologist\b", re.I),
    re.compile(r"\brespiratory therapist\b", re.I),
    re.compile(r"\black nucleus\b", re.I),
    re.compile(r"\bcontain nucleus\b", re.I),
    re.compile(r"\banswers? will vary\b", re.I),
    re.compile(r"\babout openstax\b", re.I),
    re.compile(r"\bopenstax tutor\b", re.I),
    re.compile(r"\berrata\b", re.I),
    re.compile(r"\bpreface\b", re.I),
    re.compile(r"\bseries or test conclusions\b", re.I),
]


IMPERATIVE_RE = re.compile(
    r"^\s*(find|determine|solve|calculate|use|let|sketch|graph|round|watch|visit|take|schedule|start)\b",
    re.I,
)


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _word_count(s: str) -> int:
    s = _norm_ws(s)
    return 0 if not s else len(s.split())


def _bucket(wc: int) -> Optional[str]:
    if 250 <= wc <= 499:
        return "short"
    if 500 <= wc <= 800:
        return "medium"
    if 801 <= wc <= 1200:
        return "long"
    return None


def _sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _dataset_card_min(repo_id: str) -> Dict[str, Any]:
    api = HfApi()
    info = api.dataset_info(repo_id=repo_id)
    card = getattr(info, "cardData", None) or {}
    try:
        card = dict(card)
    except Exception:
        card = card if isinstance(card, dict) else {}
    return {
        "repo_id": repo_id,
        "sha": getattr(info, "sha", None),
        "last_modified": (
            getattr(info, "lastModified", None).isoformat()
            if hasattr(getattr(info, "lastModified", None), "isoformat")
            else getattr(info, "lastModified", None)
        ),
        "license": card.get("license") or card.get("licenses") or None,
        "homepage": card.get("homepage") or None,
        "source": card.get("source") or card.get("sources") or None,
    }


def _line_looks_bad(line: str) -> bool:
    text = _norm_ws(line)
    if not text:
        return True
    if any(p.search(text) for p in HARD_LINE_PATTERNS):
        return True
    if URL_RE.search(text) and len(text.split()) <= 20:
        return True
    if SPACED_CAPS_RE.search(text) and len(text.split()) <= 18:
        return True
    return False


def _alpha_ratio(text: str) -> float:
    if not text:
        return 0.0
    alpha = sum(ch.isalpha() for ch in text)
    return alpha / max(1, len(text))


def _math_symbol_count(text: str) -> int:
    return len(MATH_SYMBOL_RE.findall(text))


def _second_person_count(text: str) -> int:
    return len(SECOND_PERSON_RE.findall(text))


def _sentence_looks_bad(sentence: str) -> bool:
    text = _norm_ws(sentence)
    if not text:
        return True
    wc = _word_count(text)
    if wc < 8:
        return True
    if re.match(r"^[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,4}:\s", text):
        return True
    if re.match(r"^[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}\)", text):
        return True
    if re.match(r"^\s*\d+\s*[–-]\s*\d+", text):
        return True
    if re.match(r"^\s*[α-ωΑ-Ω]", text):
        return True
    if URL_RE.search(text):
        return True
    if text.count("?") > 0:
        return True
    if OPTION_MARKER_RE.findall(text):
        return True
    if any(p.search(text) for p in HARD_SENTENCE_PATTERNS):
        return True
    if any(p.search(text) for p in SOFT_SENTENCE_PATTERNS):
        return True
    if IMPERATIVE_RE.match(text) and wc <= 40:
        return True
    if re.match(r"^\s*\d+(?:\.\d+)+\s+", text):
        return True
    if re.match(r"^\s*\d+\s+[A-Z]", text):
        return True
    if re.search(r"\b\d{2,3}\s+[a-z]", text):
        return True
    if re.match(r"^\s*\d+[\.\)]\s", text):
        return True
    if re.match(r"^\s*[a-d][\.\)]\s", text, flags=re.I):
        return True
    if _alpha_ratio(text) < 0.62:
        return True
    math_symbols = _math_symbol_count(text)
    if math_symbols >= 8:
        return True
    digit_count = sum(ch.isdigit() for ch in text)
    if digit_count >= 14 and _alpha_ratio(text) < 0.78:
        return True
    if _second_person_count(text) >= 2:
        return True
    if text.endswith(":"):
        return True
    return False


def _module_looks_bad(lines: Sequence[str]) -> bool:
    text = _norm_ws(" ".join(lines))
    if not text:
        return True
    if any(p.search(text) for p in MODULE_BAD_PATTERNS):
        return True
    if OPTION_MARKER_RE.findall(text):
        return True
    if text.count("?") >= 2:
        return True
    if _second_person_count(text) >= 18:
        return True
    return False


def _split_sentences(text: str) -> List[str]:
    text = _norm_ws(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=(?:[\"'(\[])?[A-Z0-9])", text)
    return [_norm_ws(part) for part in parts if _norm_ws(part)]


def _clean_module_text(lines: Sequence[str]) -> str:
    kept: List[str] = []
    for raw in lines:
        line = raw or ""
        line = CNX_URL_RE.sub("", line)
        line = re.sub(r"^\s*this openstax book is available for free at\s*", "", line, flags=re.I)
        line = _norm_ws(line)
        if _line_looks_bad(line):
            continue
        kept.append(line)
    return _norm_ws(" ".join(kept))


def _clean_sentences(lines: Sequence[str]) -> List[str]:
    module_text = _clean_module_text(lines)
    if not module_text:
        return []
    sentences = _split_sentences(module_text)
    cleaned: List[str] = []
    seen = set()
    for sentence in sentences:
        if _sentence_looks_bad(sentence):
            continue
        key = _norm_ws(sentence).lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(sentence)
    return cleaned


def _window_soft_noise_count(text: str) -> int:
    return sum(1 for pat in SOFT_WINDOW_PATTERNS if pat.search(text))


def _window_looks_good(text: str, wc: int, sentence_count: int) -> bool:
    if wc < 250 or wc > 1200:
        return False
    if sentence_count < 4:
        return False
    if URL_RE.search(text):
        return False
    if SPACED_CAPS_RE.search(text):
        return False
    if text.count("?") > 0:
        return False
    if OPTION_MARKER_RE.findall(text):
        return False
    if "latest/)" in text.lower():
        return False
    if "/)," in text or "/)" in text:
        return False
    if re.search(r"[.!?]\s+[a-z]", text):
        return False
    if _window_soft_noise_count(text) > 0:
        return False
    if _math_symbol_count(text) >= 14:
        return False
    if _second_person_count(text) >= 4:
        return False
    if _alpha_ratio(text) < 0.72:
        return False
    if not re.match(r"^[\"'(\[]?[A-Z0-9]", text):
        return False
    if text[-1] not in ".!?":
        return False
    return True


def _best_window_for_bucket(sentences: Sequence[str], bucket: str) -> Optional[Tuple[str, int]]:
    lo, hi, target = BUCKET_CONFIG[bucket]
    if not sentences:
        return None
    sent_wcs = [_word_count(s) for s in sentences]
    best: Optional[Tuple[Tuple[int, int, int, int], str, int]] = None

    for start in range(len(sentences)):
        total = 0
        for end in range(start, len(sentences)):
            total += sent_wcs[end]
            if total > hi:
                break
            if total < lo:
                continue
            chunk = " ".join(sentences[start : end + 1])
            sent_count = end - start + 1
            if not _window_looks_good(chunk, total, sent_count):
                continue
            score = (
                abs(total - target),
                sum(ch.isdigit() for ch in chunk),
                _math_symbol_count(chunk),
                -sent_count,
            )
            if best is None or score < best[0]:
                best = (score, chunk, total)

    if best is None:
        return None
    return best[1], best[2]


def iter_openstax_modules(
    stream_ds,
    progress_rows_every: int = 0,
) -> Iterable[Dict[str, Any]]:
    current_module: Optional[str] = None
    current_lines: List[str] = []
    start_row: Optional[int] = None
    end_row: Optional[int] = None

    def flush() -> Optional[Dict[str, Any]]:
        nonlocal current_module, current_lines, start_row, end_row
        if not current_module:
            current_module = None
            current_lines = []
            start_row = None
            end_row = None
            return None
        out = {
            "module": current_module,
            "source_row_idx": start_row,
            "source_row_idx_end": end_row,
            "lines": current_lines[:],
        }
        current_module = None
        current_lines = []
        start_row = None
        end_row = None
        return out

    for row_idx, row in enumerate(stream_ds):
        if progress_rows_every and row_idx > 0 and (row_idx % progress_rows_every == 0):
            print(f"[scan] rows={row_idx} in_module={bool(current_module)}", flush=True)
        line = row.get("text")
        if not isinstance(line, str):
            continue
        s = line.strip()
        if not s:
            continue

        match = CNX_URL_RE.search(s)
        if match:
            out = flush()
            if out:
                yield out
            current_module = match.group(1).lower()
            cleaned = CNX_URL_RE.sub("", s)
            cleaned = re.sub(r"^\s*this openstax book is available for free at\s*", "", cleaned, flags=re.I)
            cleaned = _norm_ws(cleaned)
            current_lines = [cleaned] if cleaned else []
            start_row = row_idx
            end_row = row_idx
            continue

        if current_module:
            current_lines.append(s)
            end_row = row_idx

    out = flush()
    if out:
        yield out


class Reservoir:
    def __init__(self, k: int, rng: random.Random):
        self.k = k
        self.rng = rng
        self.items: List[Dict[str, Any]] = []
        self.n_seen = 0

    def consider(self, item: Dict[str, Any]) -> None:
        self.n_seen += 1
        if len(self.items) < self.k:
            self.items.append(item)
            return
        idx = self.rng.randint(1, self.n_seen)
        if idx <= self.k:
            self.items[idx - 1] = item


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-total", type=int, default=250)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-modules", type=int, default=25000)
    ap.add_argument("--min-modules", type=int, default=6000)
    ap.add_argument("--progress-every", type=int, default=500)
    ap.add_argument("--progress-rows-every", type=int, default=200000)
    ap.add_argument("--output-samples", type=str, default=os.path.join(HERE, "cleaned_samples.jsonl"))
    ap.add_argument("--output-meta", type=str, default=os.path.join(HERE, "cleaned_samples.meta.json"))
    args = ap.parse_args()

    quotas = {
        "short": int(round(args.n_total * 0.20)),
        "medium": int(round(args.n_total * 0.70)),
        "long": args.n_total - int(round(args.n_total * 0.20)) - int(round(args.n_total * 0.70)),
    }
    if sum(quotas.values()) != args.n_total:
        raise SystemExit(f"Invalid quotas: {quotas}")

    rng = random.Random(args.seed)
    reservoirs = {bucket: Reservoir(quotas[bucket], rng) for bucket in quotas}
    availability = {bucket: 0 for bucket in quotas}
    cards: List[Dict[str, Any]] = []
    scanned_modules = 0
    seen_hashes = set()

    repo_id = "crumb/openstax-text"
    try:
        cards.append(_dataset_card_min(repo_id))
    except Exception as exc:
        cards.append({"repo_id": repo_id, "error": repr(exc)})

    ds_stream = load_dataset(repo_id, split="train", streaming=True)

    for module in iter_openstax_modules(ds_stream, progress_rows_every=args.progress_rows_every):
        scanned_modules += 1
        if args.max_modules and scanned_modules > args.max_modules:
            break
        if args.progress_every and (scanned_modules % args.progress_every == 0):
            have = {bucket: len(reservoirs[bucket].items) for bucket in quotas}
            print(f"[progress] modules={scanned_modules} selected={have} availability={availability}", flush=True)

        if _module_looks_bad(module["lines"]):
            continue

        sentences = _clean_sentences(module["lines"])
        if not sentences:
            continue

        for bucket in ("short", "medium", "long"):
            candidate = _best_window_for_bucket(sentences, bucket=bucket)
            if not candidate:
                continue
            text, wc = candidate
            text_hash = _sha1_text(text)
            if text_hash in seen_hashes:
                continue
            availability[bucket] += 1
            seen_hashes.add(text_hash)
            reservoirs[bucket].consider(
                {
                    "source_dataset": repo_id,
                    "source_split": "train",
                    "source_row_idx": module["source_row_idx"],
                    "source_row_idx_end": module["source_row_idx_end"],
                    "article_id": (
                        f"{repo_id}|split=train|module={module['module']}|"
                        f"rows={module['source_row_idx']}-{module['source_row_idx_end']}"
                    ),
                    "title": None,
                    "book": None,
                    "chapter": None,
                    "section": None,
                    "url": None,
                    "word_count": wc,
                    "bucket": bucket,
                    "text": text,
                    "text_sha1": text_hash,
                }
            )

        if scanned_modules >= args.min_modules and all(len(reservoirs[b].items) >= quotas[b] for b in quotas):
            print(f"[early-stop] modules={scanned_modules} filled_quotas={quotas}", flush=True)
            break

    missing = {bucket: max(0, quotas[bucket] - len(reservoirs[bucket].items)) for bucket in quotas}
    if any(missing.values()):
        raise SystemExit(
            "Not enough clean single-source items to satisfy quotas.\n"
            f"Quotas: {quotas}\n"
            f"Selected: {{bucket: len(reservoirs[bucket].items) for bucket in quotas}}\n"
            f"Missing: {missing}\n"
            f"Availability (scanned): {availability}"
        )

    samples: List[Dict[str, Any]] = []
    for bucket in ("medium", "short", "long"):
        samples.extend(reservoirs[bucket].items)
    rng.shuffle(samples)

    with open(args.output_samples, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    meta = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "generator": os.path.basename(__file__),
        "n_total": args.n_total,
        "seed": args.seed,
        "quotas": quotas,
        "selected_counts": {bucket: len(reservoirs[bucket].items) for bucket in quotas},
        "availability_scanned": availability,
        "scanned_modules": scanned_modules,
        "sources": cards,
        "bucket_definition": {
            "short": "250-499",
            "medium": "500-800",
            "long": "801-1200",
        },
        "single_source_rule": "Each sample is a sentence-aligned contiguous window from one CNX module only.",
        "quality_controls": {
            "sentence_aligned_windows": True,
            "filtered_noise": [
                "mcq and review content",
                "key terms / glossary / chapter summary",
                "learning objectives / AP scaffolding",
                "front matter and chapter openers",
                "figure/table captions, credits, and URLs",
                "instructional prompts and worked-example markers",
                "formula-dense sentences",
            ],
        },
        "outputs": {
            "samples_jsonl": os.path.abspath(args.output_samples),
            "meta_json": os.path.abspath(args.output_meta),
        },
    }

    with open(args.output_meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Wrote: {os.path.abspath(args.output_samples)}")
    print(f"Wrote: {os.path.abspath(args.output_meta)}")


if __name__ == "__main__":
    main()
