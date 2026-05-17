# This file defines all the request and response shapes used across the API.
# Pydantic validates the data automatically when these models are used in route handlers.

from pydantic import BaseModel, Field
from typing import Any, Dict, List


MAX_TEXT_CHARS = 50000


# Request body for plain text submitted by the frontend.
class TextRequest(BaseModel):
    """Request body containing raw text submitted for reading support."""

    text: str


class TTSRequest(BaseModel):
    """Request body for backend text-to-speech generation."""

    text: str = Field(..., min_length=1, max_length=12000)
    voice: str = "default-female"
    speed: float = Field(1.0, ge=0.5, le=2.0)
    volume: int = Field(70, ge=0, le=100)


# Request body for uploaded files sent as base64 content.
class ExtractFileRequest(BaseModel):
    """Request body for a TXT, PDF, or DOCX upload encoded as base64."""

    filename: str
    contentBase64: str


# Response returned after extracting readable text from a file.
class ExtractFileResponse(BaseModel):
    """Response returned after readable text is extracted from an uploaded file."""

    text: str
    sourceType: str
    usedFallback: bool
    notice: str


# A single reading block shown by the frontend result page.
class TextBlock(BaseModel):
    """One section card and summary block displayed by the frontend."""

    id: int
    title: str = ""
    subtitle: str = ""
    originalText: str
    summary: str
    keyPoints: List[str]


# Compact processing metrics exposed for debugging in the browser network tab.
class TextProcessingStats(BaseModel):
    """Timing and block-count metrics returned with a reading response."""

    totalSeconds: float = 0.0
    sectionCardSeconds: float = 0.0
    preprocessSeconds: float
    modelSeconds: float
    # Time spent on blocks that the team model could not handle.
    fallbackBlockSeconds: float = 0.0
    blockCount: int
    modelBlockCount: int
    fallbackBlockCount: int
    blockWordCounts: List[int]


# Overall document summary shown above the section cards.
class OverallSummary(BaseModel):
    """Short whole-document summary displayed above the reading blocks."""

    heading: str = ""
    text: str = ""


# Response returned after splitting and summarising reading text.
class TextResponse(BaseModel):
    """Full reading-support response returned to the frontend."""

    notice: str
    usedFallback: bool
    # Machine-readable reason for fallback, empty when the normal path succeeds.
    fallbackReason: str
    # Whether segmentation came from AI or local fallback, with detail info.
    segmentation: Dict[str, Any]
    # Kept for compatibility; the frontend now gets this from /api/plugin/summary.
    overallSummary: OverallSummary = Field(default_factory=OverallSummary)
    blocks: List[TextBlock]
    processingStats: TextProcessingStats
