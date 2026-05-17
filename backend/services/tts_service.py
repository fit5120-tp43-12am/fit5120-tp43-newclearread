# This file handles text-to-speech generation using the OpenAI TTS API.
# Generated audio is cached on disk so repeated requests for the same text
# do not make extra API calls.

import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


BACKEND_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(BACKEND_ENV_PATH)

DEFAULT_MODEL = "gpt-4o-mini-tts"
DEFAULT_TIMEOUT_SECONDS = 45

# Maps the frontend voice names to the OpenAI voice IDs
VOICE_MAP = {
    "default-female": "nova",
    "default-male": "onyx",
}


def synthesize_tts(text: str, voice: str, speed: float) -> bytes:
    """
    Convert text to speech and return the audio as WAV bytes.
    Checks the local disk cache first to avoid repeated API calls.

    Args:
        text (str): the text to read aloud
        voice (str): the voice name from the frontend, e.g. "default-female"
        speed (float): playback speed (applied by the frontend, not the API)

    Returns:
        bytes: WAV audio data

    Raises:
        RuntimeError: if the openai package is missing, the API key is not set,
                      or the OpenAI request fails
    """
    _ = speed  # Speed is applied by the frontend audio element for instant control.
    if OpenAI is None:
        raise RuntimeError("The openai package is required to call OpenAI TTS.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    model = os.getenv("OPENAI_TTS_MODEL", DEFAULT_MODEL)
    timeout_seconds = _env_int("OPENAI_TTS_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    voice_name = VOICE_MAP.get(voice, VOICE_MAP["default-female"])

    # Return the cached file if it exists
    cache_path = _cache_path(model, voice_name, text)
    if cache_path.exists():
        return cache_path.read_bytes()

    client = OpenAI(api_key=api_key, timeout=timeout_seconds)
    try:
        response = client.audio.speech.create(
            model=model,
            voice=voice_name,
            input=" ".join(text.strip().split()),
            instructions=_build_instructions(),
            response_format="wav",
        )
        wav = response.read()
    except Exception as error:
        raise RuntimeError(f"OpenAI TTS request failed: {error}") from error

    # Save to cache so future requests are instant
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(wav)
    return wav


def _build_instructions() -> str:
    """Return the speaking style instructions sent to the TTS model."""
    return "Read in clear, natural English with a calm reading-support tone."


def _cache_path(model: str, voice_name: str, text: str) -> Path:
    """
    Build a unique file path for this text/voice/model combination.

    Args:
        model (str): the TTS model name
        voice_name (str): the OpenAI voice ID
        text (str): the text that will be spoken

    Returns:
        Path: the path where the cached WAV file should be stored
    """
    raw_key = "\n".join([model, voice_name, " ".join(text.strip().split())])
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return Path(__file__).resolve().parents[1] / ".cache" / "tts" / f"{digest}.wav"


def _env_int(name: str, default: int) -> int:
    """
    Read an integer value from the environment, falling back to a default.

    Args:
        name (str): the environment variable name
        default (int): the value to use if the variable is missing or not a number

    Returns:
        int: the parsed value or the default
    """
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
