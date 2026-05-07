from pydantic import BaseModel
from typing import Any, Dict, List


MAX_TEXT_CHARS = 50000


# Request body for plain text submitted by the frontend.
class TextRequest(BaseModel):
    text: str


# Request body for uploaded files sent as base64 content.
class ExtractFileRequest(BaseModel):
    filename: str
    contentBase64: str


# Response returned after extracting readable text from a file.
class ExtractFileResponse(BaseModel):
    text: str
    sourceType: str
    usedFallback: bool
    notice: str


# A single reading block shown by the frontend result page.
class TextBlock(BaseModel):
    id: int
    # Cleaned source text for this semantic block.
    originalText: str
    # One-sentence summary generated for this block.
    summary: str
    # Short concrete points shown under the block summary.
    keyPoints: List[str]


# Response returned after splitting and summarising reading text.
class TextResponse(BaseModel):
    # Message displayed in the green result banner.
    notice: str
    # True when preprocessing or summary generation used a fallback path.
    usedFallback: bool
    # Machine-readable reason for fallback, empty when the normal path succeeds.
    fallbackReason: str
    # Explains whether block segmentation came from AI or local fallback.
    segmentation: Dict[str, Any]
    # Block list consumed directly by ReadingPage.vue.
    blocks: List[TextBlock]

