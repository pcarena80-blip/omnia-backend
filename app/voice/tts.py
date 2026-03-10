"""
Text-to-Speech (TTS) Module
Converts AI text responses to natural-sounding speech.
Uses ElevenLabs for premium voice, with browser TTS as fallback.
"""
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


async def synthesize_speech(
    text: str,
    voice_id: Optional[str] = None,
    model_id: str = "eleven_multilingual_v2",
) -> dict:
    """
    Convert text to speech audio using ElevenLabs.

    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID (default from settings)
        model_id: ElevenLabs model to use

    Returns:
        dict with 'audio_base64' or error
    """
    if not settings.elevenlabs_api_key:
        return {
            "audio_base64": None,
            "fallback": "browser_tts",
            "message": "ElevenLabs not configured. Using browser's built-in TTS.",
            "text": text,
        }

    try:
        import base64
        import httpx

        voice = voice_id or settings.elevenlabs_voice_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                headers={
                    "xi-api-key": settings.elevenlabs_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": model_id,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
                timeout=30.0,
            )
            response.raise_for_status()

            audio_base64 = base64.b64encode(response.content).decode("utf-8")

            return {
                "audio_base64": audio_base64,
                "content_type": "audio/mpeg",
                "text": text,
                "voice_id": voice,
            }

    except Exception as e:
        logger.error(f"TTS error: {e}")
        return {
            "audio_base64": None,
            "fallback": "browser_tts",
            "error": str(e),
            "text": text,
        }
