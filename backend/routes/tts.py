from fastapi import APIRouter, HTTPException, Response

from models.schemas import TTSRequest
from services.tts_service import synthesize_tts


router = APIRouter()


@router.post("/tts")
def text_to_speech(request: TTSRequest):
    try:
        audio = synthesize_tts(
            text=request.text.strip(),
            voice=request.voice,
            speed=request.speed,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )
