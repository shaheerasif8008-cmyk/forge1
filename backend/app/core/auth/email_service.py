"""Email sending via Resend; logs to console in dev.

Safe import pattern so tests don't fail if provider SDK changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

try:  # Optional import; handled gracefully if missing or API surface differs
    import resend  # type: ignore
except Exception:  # noqa: BLE001
    resend = None  # type: ignore

from ..config import settings


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EmailContent:
    to: str
    subject: str
    html: str


def _provider_available() -> bool:
    return bool(settings.resend_api_key) and resend is not None


def send_email(msg: EmailContent) -> None:
    if settings.env == "dev" or not _provider_available():
        logger.info("[DEV EMAIL] to=%s subject=%s", msg.to, msg.subject)
        logger.info("[DEV EMAIL HTML] %s", msg.html)
        return
    try:
        # Resend Python SDK pattern
        resend.api_key = settings.resend_api_key  # type: ignore[attr-defined]
        payload = {
            "from": "Forge1 <no-reply@forge1.local>",
            "to": msg.to,
            "subject": msg.subject,
            "html": msg.html,
        }
        # prefer attribute if present
        if hasattr(resend, "Emails"):
            resend.Emails.send(payload)  # type: ignore[attr-defined]
        else:
            # Fallback to function if SDK surface differs
            getattr(resend, "send_email")(payload)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        logger.warning("Email provider send failed; logging only", exc_info=True)
        logger.info("[FALLBACK EMAIL] to=%s subject=%s", msg.to, msg.subject)
        logger.info("[FALLBACK EMAIL HTML] %s", msg.html)


def make_verify_email(to: str, link: str) -> EmailContent:
    return EmailContent(
        to=to,
        subject="Verify your email",
        html=f"<p>Click to verify your email:</p><p><a href='{link}'>Verify</a></p>",
    )


def make_invite_email(to: str, link: str, tenant: str) -> EmailContent:
    return EmailContent(
        to=to,
        subject=f"You're invited to {tenant} on Forge1",
        html=f"<p>You have been invited to tenant {tenant}. Accept:</p><p><a href='{link}'>Accept invite</a></p>",
    )


def make_reset_email(to: str, link: str) -> EmailContent:
    return EmailContent(
        to=to,
        subject="Reset your Forge1 password",
        html=f"<p>Reset your password:</p><p><a href='{link}'>Reset password</a></p>",
    )


