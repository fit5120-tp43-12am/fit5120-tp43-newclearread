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
    # Process pasted text into semantic blocks, then summarise each block for the frontend.
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
    try:
        # Decode PDF/DOCX uploads into plain text before the user runs text processing.
        return extract_text_from_upload(request.filename, request.contentBase64)
    except ValueError as error:
        # Invalid input from the client is reported as a 400 response.
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        # Unexpected extraction errors are treated as server-side failures.
        raise HTTPException(status_code=500, detail=str(error)) from error

