from time import perf_counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import MAX_TEXT_CHARS, OverallSummary
from services.overall_summary_service import generate_overall_summary

router = APIRouter()


class PluginSummaryRequest(BaseModel):
    text: str = Field(..., min_length=1)


class PluginSummaryResponse(BaseModel):
    overallSummary: OverallSummary
    processingStats: dict


@router.post("/plugin/summary", response_model=PluginSummaryResponse)
def plugin_summary_api(request: PluginSummaryRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Text is too long. Maximum is {MAX_TEXT_CHARS} characters.",
        )

    start = perf_counter()
    summary = generate_overall_summary(text)
    duration_seconds = round(perf_counter() - start, 3)

    return {
        "overallSummary": summary,
        "processingStats": {
            "durationSeconds": duration_seconds,
        },
    }
