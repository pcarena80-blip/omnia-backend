"""
Twilio Service Tool
SMS and voice call capabilities via Twilio API.
"""
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


async def send_sms(to_number: str, message: str) -> dict:
    """
    Send an SMS message via Twilio.

    Args:
        to_number: Recipient phone number with country code
        message: Text message to send

    Returns:
        dict with send result
    """
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio not configured — SMS queued (mock)")
        return {
            "success": False,
            "mock": True,
            "message": "Twilio not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env",
            "queued_message": message,
        }

    try:
        # Lazy import (only when actually used)
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        sms = client.messages.create(
            body=message,
            from_=settings.twilio_phone_number,
            to=to_number,
        )

        return {
            "success": True,
            "sid": sms.sid,
            "status": sms.status,
            "to": to_number,
        }

    except Exception as e:
        logger.error(f"Twilio SMS error: {e}")
        return {"success": False, "error": str(e)}


async def make_voice_call(
    to_number: str,
    twiml_message: str,
) -> dict:
    """
    Make a voice call via Twilio.
    Uses TwiML to define what the AI says.

    Args:
        to_number: Phone number to call
        twiml_message: What the AI should say on the call

    Returns:
        dict with call result
    """
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return {
            "success": False,
            "mock": True,
            "message": "Twilio not configured for voice calls.",
        }

    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        # TwiML for the call
        twiml = f'<Response><Say voice="alice">{twiml_message}</Say></Response>'

        call = client.calls.create(
            twiml=twiml,
            from_=settings.twilio_phone_number,
            to=to_number,
        )

        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status,
            "to": to_number,
        }

    except Exception as e:
        logger.error(f"Twilio voice call error: {e}")
        return {"success": False, "error": str(e)}
