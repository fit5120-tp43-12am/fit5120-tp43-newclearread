from pydantic import BaseModel
from typing import List


# 前端传进来的数据
class TextRequest(BaseModel):
    text: str


class ExtractFileRequest(BaseModel):
    filename: str
    contentBase64: str


class ExtractFileResponse(BaseModel):
    text: str
    sourceType: str
    usedFallback: bool
    notice: str


# 后端返回的数据
class TextResponse(BaseModel):
    summary: str
    simplified: str
    keyPoints: List[str]
    usedFallback: bool
    fallbackReason: str
    notice: str
