"""
Email Service Tool
Send emails via SendGrid API or SMTP fallback.
"""
import logging
from typing import Optional, List
from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    cc: Optional[List[str]] = None,
) -> dict:
    """
    Send an email.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Plain text body
        html_body: Optional HTML version
        cc: Optional CC recipients

    Returns:
        dict with send result
    """
    # For Phase 1, we log the email (actual sending comes in Phase 4)
    logger.info(f"Email queued: to={to_email}, subject={subject}")

    return {
        "success": True,
        "mock": True,
        "message": "Email service not yet connected. Email details saved.",
        "to": to_email,
        "subject": subject,
        "body_preview": body[:100],
    }
