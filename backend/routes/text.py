from fastapi import APIRouter, HTTPException
from models.schemas import (
    ExtractFileRequest,
    ExtractFileResponse,
    TextRequest,
    TextResponse,
)
from services.file_service import extract_text_from_upload
from services.text_service import process_text

router = APIRouter()

@router.post("/process-text", response_model=TextResponse)
def process_text_api(request: TextRequest):
    # Pass user text to the service layer and return the processed result.
    result = process_text(request.text)
    return result


@router.post("/extract-text", response_model=ExtractFileResponse)
def extract_text_api(request: ExtractFileRequest):
    try:
        # Decode the uploaded file and extract plain text the frontend can display.
        return extract_text_from_upload(request.filename, request.contentBase64)
    except ValueError as error:
        # Invalid input from the client is reported as a 400 response.
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        # Unexpected extraction errors are treated as server-side failures.
        raise HTTPException(status_code=500, detail=str(error)) from error

