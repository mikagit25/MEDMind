"""Email service — sends transactional emails via SMTP or logs to console in dev."""
import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_smtp(to: str, subject: str, html: str, text: str) -> None:
    """Send via SMTP. Raises on failure."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, to, msg.as_string())


async def send_password_reset(to_email: str, reset_token: str) -> None:
    """Send password reset email (async, non-blocking)."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}&email={to_email}"

    subject = "Reset your MedMind password"
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Georgia, serif; background: #f0ede8; margin: 0; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #fff; border: 1px solid #d8d2c8; border-radius: 12px; padding: 40px;">
    <h1 style="font-family: 'Syne', sans-serif; color: #1a1814; font-size: 22px; margin: 0 0 16px;">Reset your password</h1>
    <p style="color: #4a453e; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">
      We received a request to reset your MedMind AI password. Click the button below to set a new password.
      This link expires in <strong>1 hour</strong>.
    </p>
    <a href="{reset_url}"
       style="display: inline-block; background: #c0392b; color: #fff; text-decoration: none;
              font-family: 'Syne', sans-serif; font-weight: 600; font-size: 14px;
              padding: 12px 28px; border-radius: 6px;">
      Reset Password
    </a>
    <p style="color: #8a8278; font-size: 12px; margin: 24px 0 0;">
      If you didn't request this, you can safely ignore this email.
    </p>
  </div>
</body>
</html>"""
    text = f"Reset your MedMind password:\n\n{reset_url}\n\nThis link expires in 1 hour."

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(_send_smtp, to_email, subject, html, text))
            logger.info("Password reset email sent to %s", to_email)
        except Exception as e:
            logger.error("Failed to send reset email to %s: %s", to_email, e)
            # Fall through — don't reveal email sending failure to the caller
    else:
        # Dev mode: print link to backend log
        logger.info("=" * 60)
        logger.info("DEV MODE — Password reset link for %s:", to_email)
        logger.info("%s", reset_url)
        logger.info("=" * 60)


def send_assignment_email(
    to_email: str,
    student_name: str,
    assignment_title: str,
    course_title: str,
    due_date: Optional[str] = None,
) -> None:
    """Send new assignment notification email (synchronous — for BackgroundTasks)."""
    due_str = f" (due {due_date})" if due_date else ""
    subject = f"New Assignment: {assignment_title}"
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Georgia, serif; background: #f0ede8; margin: 0; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #fff; border: 1px solid #d8d2c8; border-radius: 12px; padding: 40px;">
    <h1 style="font-family: 'Syne', sans-serif; color: #1a1814; font-size: 22px; margin: 0 0 16px;">New Assignment</h1>
    <p style="color: #4a453e; font-size: 15px; line-height: 1.6; margin: 0 0 16px;">
      Hi {student_name}, your teacher posted a new assignment in <strong>{course_title}</strong>.
    </p>
    <div style="background:#f7f4f0;border:1px solid #d8d2c8;border-radius:8px;padding:16px 20px;margin-bottom:16px;">
      <p style="font-family:sans-serif;font-size:16px;font-weight:700;color:#1a1814;margin:0;">{assignment_title}</p>
      <p style="color:#8a8278;font-size:13px;margin:4px 0 0;">{course_title}{due_str}</p>
    </div>
    <a href="{settings.FRONTEND_URL}/my-courses"
       style="display: inline-block; background: #1a1814; color: #fff; text-decoration: none;
              font-family: 'Syne', sans-serif; font-weight: 600; font-size: 14px;
              padding: 12px 28px; border-radius: 6px;">
      View Assignment
    </a>
  </div>
</body>
</html>"""
    text = f"New assignment in {course_title}: {assignment_title}{due_str}\n\n{settings.FRONTEND_URL}/my-courses"
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            _send_smtp(to_email, subject, html, text)
        except Exception as e:
            logger.error("Failed to send assignment email to %s: %s", to_email, e)
    else:
        logger.info("DEV MODE — Assignment email: %s → %s", assignment_title, to_email)


async def send_welcome_email(to_email: str, first_name: str) -> None:
    """Send welcome email after registration (async, non-blocking)."""
    subject = "Welcome to MedMind AI"
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Georgia, serif; background: #f0ede8; margin: 0; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #fff; border: 1px solid #d8d2c8; border-radius: 12px; padding: 40px;">
    <h1 style="font-family: 'Syne', sans-serif; color: #1a1814; font-size: 22px; margin: 0 0 16px;">Welcome, {first_name}!</h1>
    <p style="color: #4a453e; font-size: 15px; line-height: 1.6; margin: 0 0 16px;">
      Your MedMind AI account is ready. Start learning with AI-powered medical education.
    </p>
    <ul style="color: #4a453e; font-size: 14px; line-height: 2; padding-left: 20px;">
      <li>Access 80+ medical modules</li>
      <li>Ask your AI tutor anything</li>
      <li>Study with spaced-repetition flashcards</li>
      <li>Practice clinical cases</li>
    </ul>
    <a href="{settings.FRONTEND_URL}/dashboard"
       style="display: inline-block; background: #c0392b; color: #fff; text-decoration: none;
              font-family: 'Syne', sans-serif; font-weight: 600; font-size: 14px;
              padding: 12px 28px; border-radius: 6px; margin-top: 16px;">
      Start Learning
    </a>
  </div>
</body>
</html>"""
    text = f"Welcome to MedMind AI, {first_name}!\n\nStart learning: {settings.FRONTEND_URL}/dashboard"

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(_send_smtp, to_email, subject, html, text))
        except Exception as e:
            logger.error("Failed to send welcome email: %s", e)
    else:
        logger.info("DEV MODE — Welcome email for %s (%s)", first_name, to_email)


async def send_payment_failed_email(to_email: str, first_name: str) -> None:
    """Notify user that their subscription payment failed."""
    subject = "Action required: Payment failed for MedMind AI"
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Georgia, serif; background: #f0ede8; margin: 0; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #fff; border: 1px solid #d8d2c8; border-radius: 12px; padding: 40px;">
    <h1 style="font-family: 'Syne', sans-serif; color: #c0392b; font-size: 22px; margin: 0 0 16px;">Payment failed</h1>
    <p style="color: #4a453e; font-size: 15px; line-height: 1.6; margin: 0 0 16px;">
      Hi {first_name}, we were unable to process your MedMind AI subscription payment.
      Please update your payment method to keep your access.
    </p>
    <a href="{settings.FRONTEND_URL}/upgrade"
       style="display: inline-block; background: #c0392b; color: #fff; text-decoration: none;
              font-family: 'Syne', sans-serif; font-weight: 600; font-size: 14px;
              padding: 12px 28px; border-radius: 6px;">
      Update Payment Method
    </a>
    <p style="color: #8a8278; font-size: 12px; margin: 24px 0 0;">
      If you have questions, reply to this email.
    </p>
  </div>
</body>
</html>"""
    text = f"Hi {first_name},\n\nWe couldn't process your MedMind AI payment.\nUpdate your payment method: {settings.FRONTEND_URL}/upgrade"

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(_send_smtp, to_email, subject, html, text))
            logger.info("Payment failed email sent to %s", to_email)
        except Exception as e:
            logger.error("Failed to send payment failed email to %s: %s", to_email, e)
    else:
        logger.info("DEV MODE — Payment failed email for %s (%s)", first_name, to_email)
