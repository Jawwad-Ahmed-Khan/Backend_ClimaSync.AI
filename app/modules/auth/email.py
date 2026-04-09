"""Async email delivery for OTP codes via SMTP.

Uses aiosmtplib for non-blocking email sending as required
by the constitution's async-everything mandate.
"""

import logging

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_otp_email(
    to_email: str,
    otp: str,
    org_name: str,
) -> None:
    """Send a verification OTP email to the registering NGO.

    Args:
        to_email: Recipient email address.
        otp: The 6-digit plain-text OTP code.
        org_name: Organisation name for personalisation.
    """
    subject = f"ClimaSync.AI — Verify your email ({org_name})"
    html_body = _build_otp_html(otp, org_name)

    message = MIMEMultipart("alternative")
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(_build_otp_text(otp, org_name), "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("OTP email sent to %s for org '%s'", to_email, org_name)
    except aiosmtplib.SMTPException:
        logger.error(
            "Failed to send OTP email to %s",
            to_email,
            exc_info=True,
        )
        raise


async def send_password_reset_email(
    to_email: str,
    otp: str,
) -> None:
    """Send a password reset OTP email.

    Args:
        to_email: Recipient email address.
        otp: The 6-digit plain-text OTP code.
    """
    subject = "ClimaSync.AI — Password Reset Code"
    html_body = _build_password_reset_html(otp)

    message = MIMEMultipart("alternative")
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(_build_password_reset_text(otp), "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("Password reset OTP sent to %s", to_email)
    except aiosmtplib.SMTPException:
        logger.error(
            "Failed to send password reset email to %s",
            to_email,
            exc_info=True,
        )
        raise


def _build_otp_text(otp: str, org_name: str) -> str:
    """Build plain-text email body."""
    return (
        f"Welcome to ClimaSync.AI, {org_name}!\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
        f"If you did not request this, please ignore this email.\n"
    )


def _build_otp_html(otp: str, org_name: str) -> str:
    """Build HTML email body with styled OTP display."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;
                padding: 32px; background: #f8fafc; border-radius: 12px;">
        <h2 style="color: #1e293b; margin-bottom: 8px;">
            Welcome to ClimaSync.AI
        </h2>
        <p style="color: #475569; font-size: 14px;">
            Hi <strong>{org_name}</strong>, verify your email to complete registration.
        </p>
        <div style="background: #ffffff; border: 2px solid #e2e8f0;
                    border-radius: 8px; padding: 24px; text-align: center;
                    margin: 24px 0;">
            <p style="color: #64748b; font-size: 12px; margin: 0 0 8px;">
                Your verification code
            </p>
            <p style="font-size: 36px; font-weight: bold; letter-spacing: 8px;
                      color: #0f172a; margin: 0;">
                {otp}
            </p>
        </div>
        <p style="color: #94a3b8; font-size: 12px;">
            This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.
            If you didn't request this, ignore this email.
        </p>
    </div>
    """


def _build_password_reset_text(otp: str) -> str:
    """Build plain-text body for password reset email."""
    return (
        f"ClimaSync.AI — Password Reset\n\n"
        f"Your password reset code is: {otp}\n\n"
        f"This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
        f"If you did not request a password reset, please ignore this email "
        f"and your password will remain unchanged.\n"
    )


def _build_password_reset_html(otp: str) -> str:
    """Build HTML email body for password reset."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;
                padding: 32px; background: #fef2f2; border-radius: 12px;">
        <h2 style="color: #1e293b; margin-bottom: 8px;">
            Password Reset Request
        </h2>
        <p style="color: #475569; font-size: 14px;">
            We received a request to reset your ClimaSync.AI account password.
            Use the code below to proceed.
        </p>
        <div style="background: #ffffff; border: 2px solid #fecaca;
                    border-radius: 8px; padding: 24px; text-align: center;
                    margin: 24px 0;">
            <p style="color: #64748b; font-size: 12px; margin: 0 0 8px;">
                Your password reset code
            </p>
            <p style="font-size: 36px; font-weight: bold; letter-spacing: 8px;
                      color: #dc2626; margin: 0;">
                {otp}
            </p>
        </div>
        <p style="color: #94a3b8; font-size: 12px;">
            This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.
            If you didn't request this, ignore this email — your password
            will remain unchanged.
        </p>
    </div>
    """

