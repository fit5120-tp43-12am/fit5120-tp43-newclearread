# This file handles the /plugin/summary endpoint.
# The browser extension sends raw article text here and gets back an overall summary.

from time import perf_counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import MAX_TEXT_CHARS, OverallSummary
from services.overall_summary_service import generate_overall_summary

router = APIRouter()


# Request and response models
class PluginSummaryRequest(BaseModel):
    """Request body containing page text sent by the browser extension."""

    text: str = Field(..., min_length=1)


class PluginSummaryResponse(BaseModel):
    """Response body returned to the browser extension summary panel."""

    overallSummary: OverallSummary
    processingStats: dict


@router.post("/plugin/summary", response_model=PluginSummaryResponse)
def plugin_summary_api(request: PluginSummaryRequest):
    """
    POST /plugin/summary

    Receives raw article text from the browser extension and returns
    a short overall summary with a heading and a few sentences.

    Args:
        request (PluginSummaryRequest): the request body containing the article text

    Returns:
        PluginSummaryResponse: the overall summary and how long it took to generate

    Raises:
        HTTPException 400: if the text is empty or too long
    """
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
