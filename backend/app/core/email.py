"""
Email service for MedMind AI.

Sends transactional emails via SMTP (Gmail / any SMTP relay).
All sends are fire-and-forget via BackgroundTasks — never block the request.

Usage:
    from app.core.email import send_email_background
    background_tasks.add_task(send_email_background, to=user.email, subject="...", html="...")

    # Or use named helpers:
    from app.core.email import email_assignment, email_at_risk_alert
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

log = logging.getLogger(__name__)


def _send_smtp(to: str, subject: str, html: str, text: Optional[str] = None) -> None:
    """Synchronous SMTP send — run in a thread/background task."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        log.warning("SMTP not configured — skipping email to %s: %s", to, subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to

    if text:
        msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.sendmail(settings.EMAIL_FROM, [to], msg.as_string())
        log.info("Email sent to %s: %s", to, subject)
    except Exception as exc:
        log.error("SMTP send failed to %s: %s", to, exc)


def send_email_background(to: str, subject: str, html: str, text: Optional[str] = None) -> None:
    """Drop-in for BackgroundTasks.add_task — synchronous wrapper."""
    _send_smtp(to, subject, html, text)


# ── Email templates ────────────────────────────────────────────────────────


def _base_template(title: str, body_html: str, cta_text: Optional[str] = None, cta_url: Optional[str] = None) -> str:
    cta = ""
    if cta_text and cta_url:
        cta = f"""
        <div style="text-align:center;margin:32px 0;">
          <a href="{cta_url}"
             style="background:#1a1814;color:#ffffff;font-family:sans-serif;font-size:14px;
                    font-weight:600;padding:12px 28px;border-radius:6px;text-decoration:none;
                    display:inline-block;">
            {cta_text}
          </a>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0ede8;font-family:Georgia,serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #d8d2c8;">
        <!-- Header -->
        <tr>
          <td style="background:#1a1814;padding:24px 32px;">
            <span style="font-family:sans-serif;font-size:22px;font-weight:900;color:#ffffff;">
              Med<span style="color:#e8c97a;">Mind</span>
            </span>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <h1 style="font-family:sans-serif;font-size:20px;font-weight:700;color:#1a1814;margin:0 0 16px;">{title}</h1>
            {body_html}
            {cta}
            <hr style="border:none;border-top:1px solid #e8e4de;margin:32px 0 16px;">
            <p style="font-size:12px;color:#8a8278;margin:0;">
              MedMind AI — Medical Education Platform<br>
              <a href="{{unsubscribe_url}}" style="color:#8a8278;">Unsubscribe</a>
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def email_welcome(to: str, first_name: str, app_url: str = "") -> None:
    app_url = app_url or settings.FRONTEND_URL
    html = _base_template(
        title=f"Welcome to MedMind AI, {first_name}!",
        body_html=f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Your account is ready. Start by exploring modules, building flashcards, or chatting with the AI tutor.
          </p>
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0;">
            If you have any questions, just reply to this email.
          </p>""",
        cta_text="Go to Dashboard",
        cta_url=f"{app_url}/dashboard",
    )
    _send_smtp(to, "Welcome to MedMind AI!", html)


def email_assignment(
    to: str,
    student_name: str,
    assignment_title: str,
    course_title: str,
    due_date: Optional[str],
    app_url: str = "",
) -> None:
    app_url = app_url or settings.FRONTEND_URL
    due_str = f"<p style='color:#8a5a00;font-size:14px;margin:8px 0 0;'>Due: <strong>{due_date}</strong></p>" if due_date else ""
    html = _base_template(
        title="New Assignment",
        body_html=f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
            Hi {student_name}, your teacher has created a new assignment in <strong>{course_title}</strong>.
          </p>
          <div style="background:#f7f4f0;border:1px solid #d8d2c8;border-radius:8px;padding:16px 20px;margin-bottom:16px;">
            <p style="font-family:sans-serif;font-size:16px;font-weight:700;color:#1a1814;margin:0;">{assignment_title}</p>
            <p style="color:#8a8278;font-size:13px;margin:4px 0 0;">{course_title}</p>
            {due_str}
          </div>""",
        cta_text="View Assignment",
        cta_url=f"{app_url}/my-courses",
    )
    _send_smtp(to, f"New Assignment: {assignment_title}", html)


def email_at_risk_alert(
    to: str,
    teacher_name: str,
    course_title: str,
    at_risk_count: int,
    app_url: str = "",
    course_id: Optional[str] = None,
) -> None:
    app_url = app_url or settings.FRONTEND_URL
    course_url = f"{app_url}/teacher/courses/{course_id}/at-risk" if course_id else f"{app_url}/teacher/dashboard"
    html = _base_template(
        title="Students Need Attention",
        body_html=f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
            Hi {teacher_name}, in your course <strong>{course_title}</strong>,
            <strong style="color:#c0392b;">{at_risk_count} student{'s are' if at_risk_count != 1 else ' is'}</strong>
            at risk of falling behind based on inactivity and low completion rates.
          </p>
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0;">
            Consider reaching out to these students or adjusting the course pace.
          </p>""",
        cta_text="View At-Risk Students",
        cta_url=course_url,
    )
    _send_smtp(to, f"⚠️ {at_risk_count} students at risk in {course_title}", html)


def email_password_reset(to: str, reset_url: str) -> None:
    html = _base_template(
        title="Reset Your Password",
        body_html="""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            We received a request to reset your password. Click the button below.
            This link expires in 1 hour.
          </p>
          <p style="color:#4a453e;font-size:14px;line-height:1.6;margin:0;">
            If you didn't request this, you can safely ignore this email.
          </p>""",
        cta_text="Reset Password",
        cta_url=reset_url,
    )
    _send_smtp(to, "Reset your MedMind AI password", html)


def email_achievement(to: str, name: str, achievement_name: str, app_url: str = "") -> None:
    app_url = app_url or settings.FRONTEND_URL
    html = _base_template(
        title=f"🏅 Achievement Unlocked: {achievement_name}",
        body_html=f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Congratulations {name}! You just earned the <strong>{achievement_name}</strong> achievement.
            Keep up the great work!
          </p>""",
        cta_text="View Achievements",
        cta_url=f"{app_url}/achievements",
    )
    _send_smtp(to, f"🏅 Achievement Unlocked: {achievement_name}", html)
