# This file handles the two main text-processing endpoints:
# - /process-text: takes pasted or typed text and returns a block-based reading result
# - /extract-text: decodes a base64 PDF or DOCX file and returns the plain text

from fastapi import APIRouter, HTTPException
from models.schemas import (
    ExtractFileRequest,
    ExtractFileResponse,
    MAX_TEXT_CHARS,
    TextRequest,
    TextResponse,
)
from services.file_service import extract_text_from_upload
from services.reading_service import process_reading_text

router = APIRouter()


@router.post("/process-text", response_model=TextResponse)
def process_text_api(request: TextRequest):
    """
    POST /process-text

    Takes raw text from the frontend, splits it into semantic blocks,
    and generates a summary and key points for each block.

    Args:
        request (TextRequest): the request body containing the text to process

    Returns:
        TextResponse: a list of reading blocks with summaries and key points

    Raises:
        HTTPException 400: if the text is empty or exceeds the character limit
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Text is too long. Maximum is {MAX_TEXT_CHARS} characters.",
        )

    result = process_reading_text(text)
    return result


@router.post("/extract-text", response_model=ExtractFileResponse)
def extract_text_api(request: ExtractFileRequest):
    """
    POST /extract-text

    Accepts a base64-encoded PDF or DOCX file and returns its plain text content
    so the frontend can pass it to the text processing endpoint.

    Args:
        request (ExtractFileRequest): the request body with the filename and base64 content

    Returns:
        ExtractFileResponse: the extracted text, file type, and any truncation notice

    Raises:
        HTTPException 400: if the file type is not supported or the content is invalid
        HTTPException 500: if text extraction fails for an unexpected reason
    """
    try:
        return extract_text_from_upload(request.filename, request.contentBase64)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
