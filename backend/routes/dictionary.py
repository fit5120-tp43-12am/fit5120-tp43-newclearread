from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.morpheme_service import analyze_word

router = APIRouter()


#
class DictionaryRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=256)


class DictionaryPart(BaseModel):
    form: str
    meaning: str
    type: str  # lowercase: "prefix", "root", "suffix"


class ProcessingStats(BaseModel):
    totalSeconds: float
    wordsApiSeconds: float
    segmentSeconds: float


class DictionaryResponse(BaseModel):
    word: str
    simpleMeaning: str | None = None
    wordParts: list[DictionaryPart] | None = None
    meaningFromParts: str | None = None
    processingStats: ProcessingStats | None = None


def _build_response(raw: dict) -> dict:
    word = raw.get("word", "")
    simple_meaning = raw.get("simple_meaning") or None

    raw_parts = raw.get("parts") or []
    word_parts = []
    meaning_fragments = []

    for part in raw_parts:
        form = part.get("display") or part.get("text") or ""
        type_label = (part.get("type") or "root").lower()
        meanings = part.get("meaning") or []
        first_meaning = meanings[0] if meanings else ""

        word_parts.append(
            DictionaryPart(form=form, meaning=first_meaning, type=type_label)
        )

        if first_meaning:
            meaning_fragments.append(f"{form} ({first_meaning})")

    meaning_from_parts = " + ".join(meaning_fragments) if meaning_fragments else None

    timing = raw.get("_timing")

    return {
        "word": word,
        "simpleMeaning": simple_meaning,
        "wordParts": word_parts if word_parts else None,
        "meaningFromParts": meaning_from_parts,
        "processingStats": timing,
    }


@router.post("/dictionary", response_model=DictionaryResponse)
def dictionary_lookup(request: DictionaryRequest):
    try:
        word = request.word.strip()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty.")

        raw = analyze_word(word)
        return _build_response(raw)

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500, detail=f"Model files not found: {str(e)}"
        ) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        ) from e
