# This file handles the /tts endpoint.
# The frontend sends text here and gets back an audio file (WAV) it can play directly.

from fastapi import APIRouter, HTTPException, Response

from models.schemas import TTSRequest
from services.tts_service import synthesize_tts


router = APIRouter()


@router.post("/tts")
def text_to_speech(request: TTSRequest):
    """
    POST /tts

    Converts a piece of text into speech and returns the audio as a WAV file.
    The frontend plays the audio using an HTML audio element.

    Args:
        request (TTSRequest): the request body with the text, voice, and speed settings

    Returns:
        Response: a WAV audio file with content-type audio/wav

    Raises:
        HTTPException 502: if the TTS provider (OpenAI) returns an error
        HTTPException 500: if something else goes wrong
    """
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
