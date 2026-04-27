import re


SENTENCE_ENDINGS = (".", "!", "?", ":")

SECTION_TITLE_PATTERNS = (
    r"^[A-Z][A-Z0-9 '&/\-:]{2,}$",
    r"^\d+(\.\d+)*\.?\s+[A-Z][A-Za-z ,:&/\-]{2,}$",
)

SHORT_METADATA_FRAGMENTS = {
    "london and b",
    "properly cited.",
    "published by",
    "author manuscript",
}

MISSING_SPACE_FIXES = {
    "accuracymore": "accuracy more",
    "themean": "the mean",
    "ismore": "is more",
}


def rough_clean_text(raw_text: str) -> str:
    text = _normalize_basic_formatting(raw_text)
    lines = text.split("\n")
    lines = _remove_metadata_and_sidebar_lines(lines)
    text = "\n".join(lines)
    text = _merge_broken_lines(text)
    text = _fix_missing_word_spaces(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_basic_formatting(raw_text: str) -> str:
    text = (raw_text or "").strip()
    replacements = {
        "\r\n": "\n",
        "\r": "\n",
        "\u00a0": " ",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _remove_metadata_and_sidebar_lines(lines: list[str]) -> list[str]:
    cleaned = []
    skip_key_points = 0

    for raw_line in lines:
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue

        if skip_key_points:
            if _looks_like_section_title(line):
                skip_key_points = 0
            elif _looks_like_key_point_line(line):
                skip_key_points -= 1
                continue
            else:
                skip_key_points = 0

        if _is_key_points_heading(line):
            skip_key_points = 8
            continue

        if _is_obvious_metadata_line(line):
            continue

        cleaned.append(line)

    return cleaned


def _is_obvious_metadata_line(line: str) -> bool:
    lowered = line.lower().strip()

    if lowered in SHORT_METADATA_FRAGMENTS:
        return True

    metadata_patterns = (
        r".*\bdoi\s*:.*",
        r".*https?://doi\.org.*",
        r".*https?://.*",
        r".*\bwww\..*",
        r".*\be-?mail\b.*",
        r".*\bemail\b.*",
        r".*\bcorrespondence\b.*",
        r".*\btel\.?\b.*",
        r".*\btelephone\b.*",
        r".*\bfax\b.*",
        r".*\bcopyright\b.*",
        r".*\u00a9.*",
        r".*\ball rights reserved\b.*",
        r".*\bopen access\b.*",
        r"^review$",
        r".*\bcurrent opinion\b.*",
        r"^volume\s+\d+.*",
        r"^issue\s+\d+.*",
        r"^number\s+\d+.*",
        r"^pages?\s+\d+.*",
        r"^\d+$",
        r"^-?\s*\d+\s*-?$",
        r"^\d+\s*/\s*\d+$",
        r"^page\s+\d+(\s+of\s+\d+)?$",
    )
    if any(re.match(pattern, lowered) for pattern in metadata_patterns):
        return True

    if _looks_like_author_affiliation(line):
        return True

    if _looks_like_isolated_broken_metadata(line):
        return True

    return False


def _looks_like_author_affiliation(line: str) -> bool:
    lowered = line.lower()
    if len(line.split()) > 22:
        return False

    has_many_commas = line.count(",") >= 2
    affiliation_terms = (
        "university",
        "college",
        "department",
        "division",
        "school",
        "institute",
        "hospital",
        "centre",
        "center",
    )
    location_terms = (
        "london",
        "oxford",
        "cambridge",
        "uk",
        "usa",
        "australia",
        "canada",
        "europe",
    )

    has_affiliation = any(term in lowered for term in affiliation_terms)
    has_location = any(term in lowered for term in location_terms)
    return (has_affiliation and has_location) or (has_many_commas and has_location)


def _looks_like_isolated_broken_metadata(line: str) -> bool:
    lowered = line.lower().strip()
    words = lowered.split()

    if len(words) <= 4 and lowered in SHORT_METADATA_FRAGMENTS:
        return True

    if len(words) <= 5 and re.search(r"\b(and|of|by|inc|ltd)\b$", lowered):
        return True

    if len(words) <= 8 and any(
        term in lowered for term in ("license", "attribution", "properly cited")
    ):
        return True

    return False


def _is_key_points_heading(line: str) -> bool:
    return re.sub(r"\s+", " ", line.strip()).lower() == "key points"


def _looks_like_key_point_line(line: str) -> bool:
    if not line.strip():
        return True

    words = line.split()
    if line.lstrip().startswith(("-", "*")):
        return True
    if len(words) <= 28 and line.endswith(";"):
        return True
    if len(words) <= 28 and not line.endswith(SENTENCE_ENDINGS):
        return True
    return False


def _merge_broken_lines(text: str) -> str:
    lines = text.split("\n")
    output = []
    current = ""

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if current:
                output.append(current.strip())
                current = ""
            if output and output[-1] != "":
                output.append("")
            continue

        if not current:
            current = line
            continue

        if _should_merge_lines(current, line):
            current = _join_lines(current, line)
        else:
            output.append(current.strip())
            current = line

    if current:
        output.append(current.strip())

    return "\n".join(output)


def _should_merge_lines(previous: str, current: str) -> bool:
    if _looks_like_section_title(current):
        return False

    if previous.endswith("-"):
        return True

    if _is_broken_citation_join(previous, current):
        return True

    if _is_broken_number_join(previous, current):
        return True

    if previous.endswith(SENTENCE_ENDINGS):
        return False

    first_char = current.lstrip()[:1]
    return first_char.islower() or first_char == "("


def _join_lines(previous: str, current: str) -> str:
    if previous.endswith("-"):
        return f"{previous[:-1]}{current}"
    if _is_broken_citation_join(previous, current):
        return f"{previous}{current}"
    return f"{previous} {current}"


def _is_broken_citation_join(previous: str, current: str) -> bool:
    return bool(re.search(r"\[[^\]]*$", previous) and re.match(r"^[^\[]*\]", current))


def _is_broken_number_join(previous: str, current: str) -> bool:
    return bool(re.search(r"\b[A-Za-z]+$", previous) and re.match(r"^\d+(\.\d+)?\b", current))


def _looks_like_section_title(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.endswith(SENTENCE_ENDINGS):
        return False
    if any(re.match(pattern, stripped) for pattern in SECTION_TITLE_PATTERNS):
        return True
    known_titles = {
        "introduction",
        "dyslexia",
        "conclusion",
        "screening and assessment",
        "discussion",
        "method",
        "methods",
        "results",
        "interventions",
    }
    return stripped.lower() in known_titles


def _fix_missing_word_spaces(text: str) -> str:
    for bad, good in MISSING_SPACE_FIXES.items():
        text = re.sub(rf"\b{re.escape(bad)}\b", good, text, flags=re.IGNORECASE)

    # Conservative fixes for common function-word merges from PDF extraction.
    text = re.sub(r"\b(the)([a-z]{4,})\b", _split_known_prefix_merge, text)
    text = re.sub(r"\b(is)(more|less|likely|not)\b", r"\1 \2", text)
    return text


def _split_known_prefix_merge(match: re.Match) -> str:
    prefix = match.group(1)
    suffix = match.group(2)
    safe_suffixes = {"mean", "same", "following", "first", "second"}
    if suffix.lower() in safe_suffixes:
        return f"{prefix} {suffix}"
    return match.group(0)


if __name__ == "__main__":
    with open("backend/sample_article.txt", "r", encoding="utf-8") as f:
        sample_text = f.read()

    print(rough_clean_text(sample_text))
