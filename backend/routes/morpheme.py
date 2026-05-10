"""
Morpheme Segmentation API endpoints.

Exposes the morpheme segmenter as HTTP API routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.morpheme_service import analyze_word

router = APIRouter()


class MorphemeRequest(BaseModel):
    """Request model for morpheme analysis."""
    word: str = Field(..., min_length=1, max_length=256, description="The word to analyze")


class MorphemePart(BaseModel):
    """A morpheme part of the analyzed word."""
    text: str
    display: str
    type: str  # "Prefix", "Root", or "Suffix"
    meaning: list[str] | None = None
    matched: str | None = None
    explanation: str | None = None


class MorphemeResponse(BaseModel):
    """Response model for morpheme analysis."""
    word: str
    simple_meaning: str | None = None
    parts: list[MorphemePart] | None = None
    found: bool | None = None


@router.post("/morpheme/analyze", response_model=MorphemeResponse)
def analyze_morpheme(request: MorphemeRequest):
    """
    Analyze a word to extract its morpheme structure.
    
    Takes a word and returns its morphological breakdown into prefix/root/suffix
    components, along with meanings and definitions from the morpheme dictionary.
    
    Args:
        request: Contains the word to analyze
    
    Returns:
        MorphemeResponse with word segmentation analysis
    """
    try:
        word = request.word.strip()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty.")
        
        result = analyze_word(word)
        return result
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Model files not found: {str(e)}") from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e
