"""System-wide notification dispatcher replacing localized string-based email functions."""

import logging
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Central decoupled bus orchestrating all outbound external messaging."""

    @staticmethod
    async def dispatch_platform_alert(email: str, subject: str, message: str) -> None:
        """Raw generic email gateway via pure SMTP."""
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
            logger.info("Platform alert successfully dispatched to %s", email)
        except Exception as e:
            logger.error("Platform alert failure targeting %s: %s", email, str(e))
            raise

    @classmethod
    async def dispatch_otp_verification(cls, email: str, raw_otp: str, organization_label: str) -> None:
        """Triggered primarily by Auth modules verifying identities dynamically."""
        subject = "Confirm Your ClimaSync Account"
        body = f"""
        Welcome {organization_label},
        Your registration code is: {raw_otp}. 
        Enter this to activate your disaster response portal.
        """
        await cls.dispatch_platform_alert(email, subject, body)

    @classmethod
    async def dispatch_password_recovery(cls, email: str, raw_otp: str) -> None:
        """Emergency override triggers."""
        subject = "ClimaSync Password Recovery"
        body = f"Your override code is: {raw_otp}. This sequence expires very soon."
        await cls.dispatch_platform_alert(email, subject, body)
