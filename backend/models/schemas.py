from pydantic import BaseModel
from typing import List


# 前端传进来的数据
class TextRequest(BaseModel):
    text: str


# 后端返回的数据
class TextResponse(BaseModel):
    summary: List[str]
    simplified: str
    keyPoints: List[str]
