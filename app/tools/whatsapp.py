"""
WhatsApp Tool
Send and receive WhatsApp messages via the official WhatsApp Business Cloud API.
Falls back to a logging mock when API credentials are not configured.
"""
import logging
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"


async def send_whatsapp_message(
    to_number: str,
    message: str,
    template_name: Optional[str] = None,
) -> dict:
    """
    Send a WhatsApp message.

    Args:
        to_number: Recipient phone number with country code (e.g., "+923001234567")
        message: Text message to send
        template_name: Optional pre-approved template name

    Returns:
        dict with send result
    """
    if not settings.whatsapp_api_token or not settings.whatsapp_phone_number_id:
        logger.warning("WhatsApp API not configured — message queued (mock)")
        return {
            "success": False,
            "mock": True,
            "message": "WhatsApp not configured. Set WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env",
            "queued_message": message,
            "to": to_number,
        }

    try:
        url = f"{WHATSAPP_API_URL}/{settings.whatsapp_phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_api_token}",
            "Content-Type": "application/json",
        }

        if template_name:
            # Template message (for first-time contacts)
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number.replace("+", ""),
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"},
                },
            }
        else:
            # Regular text message
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number.replace("+", ""),
                "type": "text",
                "text": {"body": message},
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, json=payload, headers=headers, timeout=15.0
            )
            response.raise_for_status()
            data = response.json()

            return {
                "success": True,
                "message_id": data.get("messages", [{}])[0].get("id"),
                "to": to_number,
                "status": "sent",
            }

    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return {"success": False, "error": str(e)}


async def send_appointment_request(
    clinic_number: str,
    patient_name: str,
    preferred_date: str,
    preferred_time: str = "any",
    doctor_name: Optional[str] = None,
) -> dict:
    """
    Send a structured appointment booking request via WhatsApp.

    Args:
        clinic_number: Clinic's WhatsApp number
        patient_name: Patient's name
        preferred_date: Preferred date string
        preferred_time: Preferred time or "any"
        doctor_name: Optional specific doctor name
    """
    doctor_part = f" with {doctor_name}" if doctor_name else ""
    message = (
        f"Assalam o Alaikum,\n\n"
        f"I would like to book an appointment{doctor_part} "
        f"for {patient_name}.\n\n"
        f"Preferred Date: {preferred_date}\n"
        f"Preferred Time: {preferred_time}\n\n"
        f"Please let me know the available slots.\n"
        f"Thank you!"
    )

    return await send_whatsapp_message(clinic_number, message)
