import json
import os
import re
import time
from collections import Counter
from contextlib import contextmanager

from dotenv import load_dotenv
from google import genai

######1
from openai import OpenAI

# -------- config --------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
#####2
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_AI = True

PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

DEAD_LOCAL_PROXY_VALUES = {
    "http://127.0.0.1:9",
    "http://localhost:9",
    "127.0.0.1:9",
    "localhost:9",
}

RETRYABLE_ERROR_MARKERS = (
    "503",
    "unavailable",
    ######5
    # "429",
    "resource_exhausted",
    "timeout",
    "timed out",
    "temporarily",
)

RETRY_DELAYS_SECONDS = (2, 4, 8)

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "then",
    "than",
    "so",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "at",
    "by",
    "from",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "their",
    "them",
    "they",
    "he",
    "she",
    "we",
    "you",
    "i",
    "our",
    "your",
    "his",
    "her",
    "not",
    "no",
    "do",
    "does",
    "did",
    "can",
    "could",
    "should",
    "would",
    "may",
    "might",
    "will",
    "just",
    "also",
    "very",
    "more",
    "most",
    "such",
    "into",
    "about",
    "over",
    "after",
    "before",
    "through",
    "between",
    "during",
    "because",
    "while",
    "where",
    "when",
    "what",
    "which",
    "who",
    "whom",
    "how",
    "why",
}


def basic_algorithm(
    text: str,
    notice: str = "",
    fallback_reason: str = "fallback_used",
):
    summary, simplified, key_points = _build_rule_based_fallback(text)
    return {
        "summary": summary,
        "simplified": simplified,
        "keyPoints": key_points,
        "usedFallback": True,
        "fallbackReason": fallback_reason,
        "notice": notice,
    }


# Determine whether the local proxy is invalid 判断是不是无效本地代理
def _is_dead_local_proxy(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in DEAD_LOCAL_PROXY_VALUES


# Temporarily disable the proxy 临时移除代理
@contextmanager
def _without_dead_local_proxies():
    removed_proxies = {}

    for var_name in PROXY_ENV_VARS:
        proxy_value = os.environ.get(var_name)
        if _is_dead_local_proxy(proxy_value):
            removed_proxies[var_name] = proxy_value
            os.environ.pop(var_name, None)

    try:
        yield
    finally:
        os.environ.update(removed_proxies)


def _is_retryable_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(marker in message for marker in RETRYABLE_ERROR_MARKERS)


def _fallback_notice(reason: str) -> str:
    notices = {
        "temporary_ai_unavailable": "AI service is busy right now. Showing a basic result.",
        "config_error": "AI is not configured right now. Showing a basic result.",
        "invalid_ai_response": "AI response could not be processed. Showing a basic result.",
        "unknown_error": "AI is unavailable right now. Showing a basic result.",
    }
    return notices.get(reason, notices["unknown_error"])


def _normalize_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_sentences(text: str) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+|\n+", normalized)
    return [part.strip(" -\t") for part in parts if part and part.strip(" -\t")]


def _tokenize_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text.lower())


def _keyword_weights(sentences: list[str]) -> Counter:
    counter = Counter()
    for sentence in sentences:
        for token in _tokenize_words(sentence):
            if len(token) >= 4 and token not in STOPWORDS:
                counter[token] += 1
    return counter


def _sentence_score(
    sentence: str, keyword_weights: Counter, sentence_index: int
) -> float:
    tokens = _tokenize_words(sentence)
    if not tokens:
        return 0

    keyword_score = sum(keyword_weights.get(token, 0) for token in tokens)
    length_bonus = min(len(tokens), 24) / 24
    early_bonus = 1.2 if sentence_index == 0 else 0.0
    return keyword_score + length_bonus + early_bonus


def _pick_summary_sentence(sentences: list[str]) -> str:
    if not sentences:
        return ""

    keyword_weights = _keyword_weights(sentences)
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: _sentence_score(item[1], keyword_weights, item[0]),
        reverse=True,
    )
    best_sentence = ranked[0][1]
    return best_sentence[:220].strip()


def _split_long_sentence(sentence: str, max_words: int = 22) -> list[str]:
    words = sentence.split()
    if len(words) <= max_words:
        return [sentence.strip()]

    clauses = re.split(r"(?<=,|;|:)\s+", sentence)
    result = []
    buffer = []

    for clause in clauses:
        clause_words = clause.split()
        if len(buffer) + len(clause_words) <= max_words:
            buffer.extend(clause_words)
            continue

        if buffer:
            result.append(" ".join(buffer).strip(" ,;:"))
            buffer = []

        if len(clause_words) <= max_words:
            buffer = clause_words
            continue

        for index in range(0, len(clause_words), max_words):
            chunk = clause_words[index : index + max_words]
            result.append(" ".join(chunk).strip(" ,;:"))

    if buffer:
        result.append(" ".join(buffer).strip(" ,;:"))

    return [part for part in result if part]


def _simplify_text(sentences: list[str]) -> str:
    simplified_parts = []
    for sentence in sentences:
        cleaned = re.sub(r"\s+", " ", sentence).strip()
        for part in _split_long_sentence(cleaned):
            if part and part[-1] not in ".!?。！？":
                part = f"{part}."
            simplified_parts.append(part)

    if not simplified_parts:
        return ""

    paragraphs = []
    current = []
    for part in simplified_parts:
        current.append(part)
        if len(current) == 2:
            paragraphs.append(" ".join(current))
            current = []

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def _pick_key_points(sentences: list[str]) -> list[str]:
    if not sentences:
        return []

    keyword_weights = _keyword_weights(sentences)
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: _sentence_score(item[1], keyword_weights, item[0]),
        reverse=True,
    )

    selected = []
    seen = set()
    for _, sentence in ranked:
        candidate = sentence.strip()
        candidate_key = candidate.lower()
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        selected.append(candidate[:140].strip())
        if len(selected) == 3:
            break

    if len(selected) < 3:
        for sentence in sentences:
            candidate = sentence.strip()
            candidate_key = candidate.lower()
            if candidate_key in seen:
                continue
            seen.add(candidate_key)
            selected.append(candidate[:140].strip())
            if len(selected) == 3:
                break

    return selected


def _build_rule_based_fallback(text: str) -> tuple[str, str, list[str]]:
    normalized = _normalize_text(text)
    if not normalized:
        return "", "", []

    sentences = _split_sentences(normalized)
    if not sentences:
        short_text = normalized[:220].strip()
        return short_text, short_text, [short_text] if short_text else []

    summary = _pick_summary_sentence(sentences)
    simplified = _simplify_text(sentences)
    key_points = _pick_key_points(sentences)

    if not summary:
        summary = sentences[0][:220].strip()

    if not simplified:
        simplified = normalized[:1000].strip()

    if not key_points:
        key_points = [sentences[0][:140].strip()]

    return summary, simplified, key_points


def _build_prompt(text: str) -> str:
    return f"""
You must return ONLY valid JSON.

Do not include:
- markdown
- explanation
- code block

Strict format:
{{
    "summary": "...",
    "simplified": "...",
    "keyPoints": ["...", "...", "..."]
}}

Core principle:
- Do NOT add new ideas
- Do NOT infer or exaggerate
- Stay strictly faithful to the original text

Requirements:

The output language must match the input text language.

1. summary:
- exactly 1 sentence
- capture the main idea of the text
- do NOT include interpretations or conclusions not clearly stated
- avoid strong claims unless explicitly stated in the text

2. simplified:
- rewrite the text in simpler language, using the same language as the input
- keep ALL key ideas from the original
- do NOT remove important details
- use shorter sentences and simpler, more common words
- prefer clear and easy-to-read wording
- avoid complex or uncommon vocabulary
- make the text easier to read for users who may struggle with complex sentences
- do NOT add new meaning

3. keyPoints:
- exactly 3 bullet points
- each point must reflect something clearly stated in the text
- do NOT generalize or combine multiple ideas into one new idea
- avoid abstract wording, stay concrete


Text:
{text}
"""


def _parse_gemini_response(response_text: str):
    if not response_text:
        raise ValueError("Empty response")

    content = response_text.strip()
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        content = match.group()
    else:
        raise ValueError("No JSON found")

    data = json.loads(content)
    data["usedFallback"] = False
    data["fallbackReason"] = ""
    data["notice"] = ""
    return data


def use_gemini(text: str):
    print(f"calling gemini with model={GEMINI_MODEL}...")
    prompt = _build_prompt(text)
    total_attempts = len(RETRY_DELAYS_SECONDS) + 1

    for attempt in range(total_attempts):
        try:
            with _without_dead_local_proxies():
                client = genai.Client(
                    api_key=GEMINI_API_KEY,
                    http_options={"api_version": "v1"},
                )
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                )

            print("RAW RESPONSE:")
            print(response.text)
            return _parse_gemini_response(response.text)

        except Exception as e:
            is_retryable = _is_retryable_error(e)
            has_retry_left = attempt < len(RETRY_DELAYS_SECONDS)
            print(f"Gemini error on attempt {attempt + 1}/{total_attempts}: {e}")

            if is_retryable and has_retry_left:
                delay = RETRY_DELAYS_SECONDS[attempt]
                print(f"Retrying Gemini in {delay} seconds...")
                time.sleep(delay)
                continue

            error_text = str(e).lower()
            if is_retryable:
                fallback_reason = "temporary_ai_unavailable"
            elif "json" in error_text or "no json found" in error_text:
                fallback_reason = "invalid_ai_response"
            else:
                fallback_reason = "unknown_error"

            return basic_algorithm(
                text,
                notice=_fallback_notice(fallback_reason),
                fallback_reason=fallback_reason,
            )


######3
def use_openai(text: str):
    print("calling openai...")

    prompt = _build_prompt(text)

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        print("RAW OPENAI RESPONSE:")
        print(content)

        return _parse_gemini_response(content)

    except Exception as e:
        print("OpenAI error:", e)

        return basic_algorithm(
            text,
            notice=_fallback_notice("temporary_ai_unavailable"),
            fallback_reason="temporary_ai_unavailable",
        )


def process_text(text: str):
    print("process_text called")

    if not USE_AI:
        print("AI disabled -> fallback")
        return basic_algorithm(
            text,
            notice=_fallback_notice("config_error"),
            fallback_reason="config_error",
        )

    if not GEMINI_API_KEY:
        print("No API key -> fallback")
        return basic_algorithm(
            text,
            notice=_fallback_notice("config_error"),
            fallback_reason="config_error",
        )

    # try:
    #     return use_gemini(text)
    # except Exception as e:
    #     print("Gemini error -> fallback:", e)
    #     return basic_algorithm(
    #         text,
    #         notice=_fallback_notice("unknown_error"),
    #         fallback_reason="unknown_error",
    #     )
    #####4
    try:
        return use_openai(text)
    except Exception as e:
        print("OpenAI failed, fallback to Gemini:", e)

        try:
            return use_gemini(text)
        except Exception as e2:
            print("Gemini error -> fallback:", e2)
            return basic_algorithm(
                text,
                notice=_fallback_notice("unknown_error"),
                fallback_reason="unknown_error",
            )
