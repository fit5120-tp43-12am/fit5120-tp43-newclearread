from pydantic import BaseModel
from typing import List


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


# Response returned after summarising and simplifying text.
class TextResponse(BaseModel):
    summary: str
    simplified: str
    keyPoints: List[str]
    usedFallback: bool
    fallbackReason: str
    notice: str

