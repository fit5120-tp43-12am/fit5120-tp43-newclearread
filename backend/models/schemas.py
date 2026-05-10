from pydantic import BaseModel, Field
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
    # Short section title shown on the section card.
    title: str = ""
    # One-line section description shown under the section title.
    subtitle: str = ""
    # Cleaned source text for this semantic block.
    originalText: str
    # One-sentence summary generated for this block.
    summary: str
    # Short concrete points shown under the block summary.
    keyPoints: List[str]


# Compact processing metrics exposed for debugging in the browser network response.
class TextProcessingStats(BaseModel):
    # Total time spent processing the request end to end.
    totalSeconds: float = 0.0
    # Time spent generating the whole-document overview summary.
    overallSummarySeconds: float = 0.0
    # Time spent cleaning, splitting sentences, and building reading blocks.
    preprocessSeconds: float
    # Time spent calling the team summary model.
    modelSeconds: float
    # Number of blocks returned to the frontend.
    blockCount: int
    # Number of blocks sent to the team summary model.
    modelBlockCount: int
    # Number of blocks handled by fallback summarisation.
    fallbackBlockCount: int
    # Word count for each returned block, in block order.
    blockWordCounts: List[int]


# Overall document summary shown above the section cards.
class OverallSummary(BaseModel):
    heading: str = ""
    text: str = ""


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
    # Short whole-document summary shown at the top of the result page.
    overallSummary: OverallSummary = Field(default_factory=OverallSummary)
    # Block list consumed directly by ReadingPage.vue.
    blocks: List[TextBlock]
    # Compact timing and block-count data for browser Network response debugging.
    processingStats: TextProcessingStats

