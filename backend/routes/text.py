from fastapi import APIRouter
from models.schemas import TextRequest, TextResponse
from services.text_service import process_text

router = APIRouter()

@router.post("/process-text", response_model=TextResponse)
def process_text_api(request: TextRequest):
    result = process_text(request.text)
    return result