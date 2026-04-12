import re


def process_text(text: str):
    # split sentences

    sentences = re.split(r"[.!?]", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # fake summary（先用简单逻辑）
    summary = sentences[0] if sentences else ""

    # fake keywords
    words = text.split()
    keywords = words[:3]

    return {
        "sentences": [s.strip() for s in sentences if s.strip()],
        "summary": summary.strip(),
        "keywords": keywords,
    }
