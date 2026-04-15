from fastapi import APIRouter, HTTPException
from backend.models.schemas import (
    ExtractFileRequest,
    ExtractFileResponse,
    TextRequest,
    TextResponse,
)
from backend.services.file_service import extract_text_from_upload
from backend.services.text_service import process_text

router = APIRouter()

@router.post("/process-text", response_model=TextResponse)
def process_text_api(request: TextRequest):
    result = process_text(request.text)
    return result


@router.post("/extract-text", response_model=ExtractFileResponse)
def extract_text_api(request: ExtractFileRequest):
    try:
        return extract_text_from_upload(request.filename, request.contentBase64)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
