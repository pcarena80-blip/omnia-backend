"""
Speech-to-Text (STT) Module
Converts voice audio to text using OpenAI Whisper API.
Client-side Web Speech API is used as the primary (free) option;
this module handles server-side transcription for uploaded audio files.
"""
import logging
import tempfile
from pathlib import Path
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


async def transcribe_audio(
    audio_data: bytes,
    filename: str = "audio.webm",
    language: Optional[str] = None,
) -> dict:
    """
    Transcribe audio to text using OpenAI Whisper API.

    Args:
        audio_data: Raw audio bytes (supports webm, mp3, wav, m4a, etc.)
        filename: Original filename (helps Whisper detect format)
        language: Optional language code (e.g., "en", "ur" for Urdu)

    Returns:
        dict with 'text' transcription and metadata
    """
    if not settings.openai_api_key:
        return {
            "text": "",
            "error": "Whisper API requires OPENAI_API_KEY. Use browser's Web Speech API for free STT.",
        }

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Save audio to temp file (Whisper needs a file)
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        with open(temp_path, "rb") as audio_file:
            params = {
                "model": "whisper-1",
                "file": audio_file,
                "response_format": "verbose_json",
            }
            if language:
                params["language"] = language

            transcript = await client.audio.transcriptions.create(**params)

        # Cleanup temp file
        Path(temp_path).unlink(missing_ok=True)

        return {
            "text": transcript.text,
            "language": getattr(transcript, "language", None),
            "duration": getattr(transcript, "duration", None),
        }

    except Exception as e:
        logger.error(f"STT error: {e}")
        return {"text": "", "error": str(e)}
