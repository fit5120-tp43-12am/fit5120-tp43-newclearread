from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.word_dictionary import WordBreakdownResponse, lookup_word_breakdown

router = APIRouter()


#
class DictionaryRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=256)


class DictionaryPart(BaseModel):
    form: str
    meaning: str
    type: str


class DictionaryResponse(BaseModel):
    word: str
    simpleMeaning: str | None = None
    wordParts: list[DictionaryPart] | None = None
    meaningFromParts: str | None = None
    processingStats: dict | None = None


def _build_response(raw: WordBreakdownResponse) -> dict:
    word_parts = []
    meaning_fragments = []

    for part in raw.parts:
        form = part.display or part.text or ""
        type_label = str(part.type).lower()
        first_meaning = part.meaning or ""

        word_parts.append(
            DictionaryPart(form=form, meaning=first_meaning, type=type_label)
        )

        if first_meaning:
            meaning_fragments.append(f"{form} ({first_meaning})")

    meaning_from_parts = " + ".join(meaning_fragments) if meaning_fragments else None

    return {
        "word": raw.word,
        "simpleMeaning": raw.simple_meaning or None,
        "wordParts": word_parts if word_parts else None,
        "meaningFromParts": meaning_from_parts,
        "processingStats": None,
    }


@router.post("/dictionary", response_model=DictionaryResponse)
def dictionary_lookup(request: DictionaryRequest):
    try:
        raw = lookup_word_breakdown(request.word)
        return _build_response(raw)

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        ) from e
