# This file handles the /dictionary API endpoint.
# When the frontend sends a word, this file looks it up and returns
# a breakdown of the word's parts and a simple meaning.

from time import perf_counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.word_dictionary import (
    WordBreakdownResponse,
    get_processing_metadata,
    lookup_word_breakdown,
)

router = APIRouter()


# Request model
class DictionaryRequest(BaseModel):
    """Request body containing the word to analyse."""

    word: str = Field(..., min_length=1, max_length=256)


# Represents one part of a word (e.g. a prefix, root, or suffix)
class DictionaryPart(BaseModel):
    """One prefix, root, base word, or suffix returned by the dictionary API."""

    form: str
    meaning: str
    type: str


# Response model
class DictionaryResponse(BaseModel):
    """Response body containing a simple meaning and optional word-part analysis."""

    word: str
    simpleMeaning: str | None = None
    wordParts: list[DictionaryPart] | None = None
    meaningFromParts: str | None = None
    processingStats: dict | None = None


def _build_response(raw: WordBreakdownResponse, duration_ms: int) -> dict:
    """
    Turn the raw lookup result into a clean dict that matches DictionaryResponse.

    Args:
        raw (WordBreakdownResponse): the result returned by the word lookup service
        duration_ms (int): how long the lookup took, in milliseconds

    Returns:
        dict: a dictionary ready to be returned as the API response
    """
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

    # Join all fragments, e.g. "bio (life) + logy (study of)"
    meaning_from_parts = " + ".join(meaning_fragments) if meaning_fragments else None

    processing_stats = get_processing_metadata(raw)
    processing_stats["durationSeconds"] = round(duration_ms / 1000, 3)

    return {
        "word": raw.word,
        "simpleMeaning": raw.simple_meaning or None,
        "wordParts": word_parts if word_parts else None,
        "meaningFromParts": meaning_from_parts,
        "processingStats": processing_stats,
    }


@router.post("/dictionary", response_model=DictionaryResponse)
def dictionary_lookup(request: DictionaryRequest):
    """
    POST /dictionary

    Receives a word from the frontend, looks it up, and returns a breakdown
    of its parts along with a simple meaning.

    Args:
        request (DictionaryRequest): the request body containing the word to look up

    Returns:
        DictionaryResponse: the word breakdown and simple meaning

    Raises:
        HTTPException 500: if the lookup fails for any reason
    """
    start = perf_counter()

    try:
        raw = lookup_word_breakdown(request.word)
        duration_ms = round((perf_counter() - start) * 1000)
        return _build_response(raw, duration_ms)

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        ) from e
