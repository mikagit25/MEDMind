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


async def send_reviewer_digest(
    to_email: str,
    reviewer_name: str,
    queue_count: int,
    feedback_count: int,
) -> None:
    """Weekly digest for content reviewers: queue depth + unresolved feedback."""
    subject = "MedMind Reviewer Weekly Digest"
    queue_url = f"{settings.FRONTEND_URL}/admin/reviewer"

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Georgia, serif; background: #f0ede8; margin: 0; padding: 40px 20px;">
  <div style="max-width: 520px; margin: 0 auto; background: #fff; border: 1px solid #d8d2c8; border-radius: 12px; padding: 40px;">
    <h1 style="font-family: 'Syne', sans-serif; color: #1a1814; font-size: 22px; margin: 0 0 8px;">Weekly Reviewer Digest</h1>
    <p style="color: #8a8278; font-size: 13px; margin: 0 0 24px;">Hi {reviewer_name} — here's your weekly summary.</p>

    <div style="display:flex; gap:16px; margin-bottom:24px;">
      <div style="flex:1; background:#fff7ed; border:1px solid #fed7aa; border-radius:8px; padding:16px 20px; text-align:center;">
        <div style="font-family:'Syne',sans-serif; font-size:32px; font-weight:800; color:#c2410c;">{queue_count}</div>
        <div style="font-family:'Syne',sans-serif; font-size:11px; font-weight:600; color:#9a3412; text-transform:uppercase; letter-spacing:.05em;">Articles Awaiting Review</div>
      </div>
      <div style="flex:1; background:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:16px 20px; text-align:center;">
        <div style="font-family:'Syne',sans-serif; font-size:32px; font-weight:800; color:#b91c1c;">{feedback_count}</div>
        <div style="font-family:'Syne',sans-serif; font-size:11px; font-weight:600; color:#991b1b; text-transform:uppercase; letter-spacing:.05em;">Unresolved Content Feedback</div>
      </div>
    </div>

    {"<p style='color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 20px;'><strong>" + str(queue_count) + " article" + ("s" if queue_count != 1 else "") + "</strong> have passed AI verification and are waiting for your expert review before being fully published.</p>" if queue_count else "<p style='color:#8a8278;font-size:14px;'>No articles currently pending your review. Check back next week!</p>"}

    <a href="{queue_url}"
       style="display:inline-block; background:#1a1814; color:#fff; text-decoration:none;
              font-family:'Syne',sans-serif; font-weight:600; font-size:14px;
              padding:12px 28px; border-radius:6px;">
      Open Reviewer Queue →
    </a>

    <p style="color: #8a8278; font-size: 12px; margin: 28px 0 0; border-top: 1px solid #e8e3db; padding-top: 16px;">
      You're receiving this because you're a reviewer on the MedMind editorial team.
      Contact <a href="mailto:editorial@medmind.pro" style="color:#c0392b;">editorial@medmind.pro</a> to unsubscribe.
    </p>
  </div>
</body>
</html>"""
    text = (
        f"MedMind Weekly Reviewer Digest — {reviewer_name}\n\n"
        f"Articles awaiting review: {queue_count}\n"
        f"Unresolved content feedback: {feedback_count}\n\n"
        f"Open queue: {queue_url}"
    )

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(_send_smtp, to_email, subject, html, text))
            logger.info("Reviewer digest sent to %s", to_email)
        except Exception as e:
            logger.error("Failed to send reviewer digest to %s: %s", to_email, e)
    else:
        logger.info(
            "DEV MODE — Reviewer digest for %s: queue=%d feedback=%d",
            to_email, queue_count, feedback_count,
        )


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


async def send_enterprise_lead_notification(
    first_name: str,
    last_name: str,
    email: str,
    company: str,
    job_title: str,
    team_size: str,
    use_case: str,
    message: str | None,
) -> None:
    """Notify admin of a new enterprise demo request."""
    from app.core.config import settings
    to_email = "partners@medmind.pro"
    subject  = f"[MedMind Enterprise] New lead: {company} — {job_title}"

    rows = [
        ("Name",      f"{first_name} {last_name}"),
        ("Email",     email),
        ("Company",   company),
        ("Job Title", job_title),
        ("Team Size", team_size),
        ("Use Case",  use_case),
        ("Message",   message or "—"),
    ]
    rows_html = "".join(
        f'<tr><td style="padding:6px 12px;font-weight:600;color:#4a453e;white-space:nowrap">{k}</td>'
        f'<td style="padding:6px 12px;color:#1a1814">{v}</td></tr>'
        for k, v in rows
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Georgia,serif;background:#f0ede8;margin:0;padding:40px 20px;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border:1px solid #d8d2c8;border-radius:12px;padding:40px;">
    <h1 style="font-family:sans-serif;color:#1a1814;font-size:20px;margin:0 0 8px;">
      🏢 New Enterprise Lead
    </h1>
    <p style="color:#8a8278;font-size:13px;margin:0 0 24px;">
      Submitted via medmind.pro/enterprise
    </p>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      {rows_html}
    </table>
    <div style="margin-top:24px;padding:12px 16px;background:#f0ede8;border-radius:8px;">
      <a href="https://medmind.pro/admin?tab=enterprise"
         style="color:#c0392b;font-weight:600;text-decoration:none;font-size:13px;">
        View in admin panel →
      </a>
    </div>
  </div>
</body></html>"""

    text = "\n".join(f"{k}: {v}" for k, v in rows)

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(_send_smtp, to_email, subject, html, text))
            logger.info("Enterprise lead notification sent: %s <%s>", company, email)
        except Exception as e:
            logger.error("Failed to send enterprise lead notification: %s", e)
    else:
        logger.info("=" * 60)
        logger.info("DEV MODE — New enterprise lead: %s <%s> @ %s", first_name, email, company)
        logger.info("=" * 60)


async def send_flashcard_reminder(
    to_email: str,
    first_name: str,
    due_count: int,
    streak_days: int = 0,
    srs_due: int = 0,
) -> None:
    """Send daily flashcard (and optional SRS lesson) due reminder email."""
    dashboard_url = f"{settings.FRONTEND_URL}/flashcards"
    srs_url = f"{settings.FRONTEND_URL}/srs-review"
    name = first_name or "there"

    streak_line = ""
    if streak_days > 0:
        streak_line = f'<p style="color:#e67e22;font-size:14px;font-weight:600;margin:0 0 16px;">🔥 Keep your {streak_days}-day streak going!</p>'

    srs_block = ""
    if srs_due > 0:
        srs_block = (
            f'<p style="color:#4a453e;font-size:15px;line-height:1.6;margin:16px 0 8px;">'
            f'+ <strong>{srs_due} lesson review{"s" if srs_due != 1 else ""}</strong> due via spaced repetition.</p>'
            f'<a href="{srs_url}" style="display:inline-block;background:#2980b9;color:#fff;text-decoration:none;'
            f'font-family:\'Syne\',sans-serif;font-weight:700;font-size:13px;'
            f'padding:10px 22px;border-radius:6px;margin-bottom:16px;">'
            f'Review {srs_due} lesson{"s" if srs_due != 1 else ""} →</a>'
        )

    if due_count > 0 and srs_due > 0:
        subject = f"📚 {due_count} flashcards + {srs_due} lesson reviews due today"
    elif srs_due > 0:
        subject = f"📖 {srs_due} lesson review{'s' if srs_due != 1 else ''} ready for spaced repetition"
    else:
        subject = f"📚 {due_count} flashcard{'s' if due_count != 1 else ''} ready for review"

    cards_block = ""
    if due_count > 0:
        cards_block = (
            f'<p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">'
            f'You have <strong>{due_count} card{"s" if due_count != 1 else ""}</strong> scheduled for review today using '
            f'spaced repetition. Reviewing them now locks them into long-term memory.</p>'
            f'{streak_line}'
            f'<a href="{dashboard_url}" style="display:inline-block;background:#c0392b;color:#fff;text-decoration:none;'
            f'font-family:\'Syne\',sans-serif;font-weight:700;font-size:14px;'
            f'padding:13px 28px;border-radius:6px;margin-bottom:16px;">'
            f'Review {due_count} card{"s" if due_count != 1 else ""} now →</a>'
        )
    else:
        cards_block = streak_line

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Georgia,serif;background:#f0ede8;margin:0;padding:40px 20px;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border:1px solid #d8d2c8;border-radius:12px;padding:40px;">
    <div style="font-family:'Syne',sans-serif;font-weight:900;font-size:22px;color:#1a1814;margin:0 0 24px;">
      Med<span style="color:#c0392b;">Mind</span>
    </div>
    <h1 style="font-family:'Syne',sans-serif;color:#1a1814;font-size:20px;margin:0 0 12px;">
      Hi {name}, your study queue is ready
    </h1>
    {cards_block}
    {srs_block}
    <p style="color:#8a8278;font-size:11px;margin:24px 0 0;">
      MedMind AI · <a href="{settings.FRONTEND_URL}/settings" style="color:#8a8278;">Manage notifications</a>
    </p>
  </div>
</body></html>"""

    text_parts = [f"Hi {name},\n"]
    if due_count > 0:
        text_parts.append(f"You have {due_count} flashcard(s) ready for spaced-repetition review.")
        text_parts.append(f"Review now: {dashboard_url}")
    if srs_due > 0:
        text_parts.append(f"You also have {srs_due} lesson review(s) due.")
        text_parts.append(f"Review lessons: {srs_url}")
    if streak_days > 0:
        text_parts.append(f"Keep your {streak_days}-day streak going!")
    text_parts.append("\nMedMind AI")
    text = "\n".join(text_parts)

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(_send_smtp, to_email, subject, html, text))
            logger.info("Study reminder sent to %s (cards=%d srs=%d)", to_email, due_count, srs_due)
        except Exception as e:
            logger.error("Failed to send flashcard reminder to %s: %s", to_email, e)
    else:
        logger.info("DEV MODE — study reminder for %s: %d cards, %d srs due", to_email, due_count, srs_due)


async def send_streak_at_risk(to_email: str, first_name: str, streak_days: int) -> None:
    """Send evening streak-at-risk warning email."""
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
    name = first_name or "there"

    subject = f"🔥 Don't break your {streak_days}-day streak!"
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Georgia,serif;background:#f0ede8;margin:0;padding:40px 20px;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border:1px solid #d8d2c8;border-radius:12px;padding:40px;">
    <div style="font-family:'Syne',sans-serif;font-weight:900;font-size:22px;color:#1a1814;margin:0 0 24px;">
      Med<span style="color:#c0392b;">Mind</span>
    </div>
    <h1 style="font-family:'Syne',sans-serif;color:#e67e22;font-size:22px;margin:0 0 12px;">
      🔥 {streak_days}-day streak at risk!
    </h1>
    <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 20px;">
      Hi {name}! You haven't studied yet today. Your {streak_days}-day streak will reset at midnight.
      Just 5 minutes of review will keep it alive.
    </p>
    <a href="{dashboard_url}"
       style="display:inline-block;background:#e67e22;color:#fff;text-decoration:none;
              font-family:'Syne',sans-serif;font-weight:700;font-size:14px;
              padding:13px 28px;border-radius:6px;margin-bottom:24px;">
      Study now — keep your streak →
    </a>
    <p style="color:#8a8278;font-size:11px;margin:0;">
      MedMind AI · <a href="{settings.FRONTEND_URL}/settings" style="color:#8a8278;">Manage notifications</a>
    </p>
  </div>
</body></html>"""
    text = (
        f"Hi {name}!\n\nYour {streak_days}-day streak will reset at midnight if you don't study today.\n"
        f"Just 5 minutes of review will keep it alive.\n\nStudy now: {dashboard_url}\n\nMedMind AI"
    )

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(_send_smtp, to_email, subject, html, text))
            logger.info("Streak-at-risk email sent to %s (streak=%d)", to_email, streak_days)
        except Exception as e:
            logger.error("Failed to send streak email to %s: %s", to_email, e)
    else:
        logger.info("DEV MODE — streak-at-risk email for %s: %d days", to_email, streak_days)


async def send_exam_survey(
    to_email: str,
    first_name: str,
    exam_outcome_id: str,
    exam_slug: str,
    reminder_number: int = 1,
) -> None:
    """Send post-exam outcome survey email."""
    name = first_name or "there"
    exam_label = exam_slug.upper()
    survey_url = f"{settings.FRONTEND_URL}/survey/exam-outcome/{exam_outcome_id}"
    unsubscribe_url = f"{settings.FRONTEND_URL}/survey/exam-outcome/{exam_outcome_id}/unsubscribe"

    reminder_note = ""
    if reminder_number > 1:
        reminder_note = '<p style="color:#8a8278;font-size:13px;margin:0 0 16px;">This is a gentle reminder — you can always opt out below.</p>'

    subject = f"How did your {exam_label} exam go?" if reminder_number == 1 else f"Still time to share your {exam_label} exam experience"
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Georgia,serif;background:#f0ede8;margin:0;padding:40px 20px;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border:1px solid #d8d2c8;border-radius:12px;padding:40px;">
    <div style="font-family:'Syne',sans-serif;font-weight:900;font-size:22px;color:#1a1814;margin:0 0 24px;">
      Med<span style="color:#c0392b;">Mind</span>
    </div>
    <h1 style="font-family:'Syne',sans-serif;color:#1a1814;font-size:20px;margin:0 0 12px;">
      Hi {name}, how did your {exam_label} go?
    </h1>
    {reminder_note}
    <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
      It takes 2 minutes and helps us improve MedMind for everyone preparing for {exam_label}.
    </p>
    <div style="background:#fef9f0;border:1px solid #f5e8c8;border-radius:8px;padding:16px;margin:0 0 20px;">
      <p style="color:#8a6a20;font-size:12px;margin:0;font-weight:600;">IMPORTANT — NDA NOTICE</p>
      <p style="color:#8a6a20;font-size:12px;margin:6px 0 0;line-height:1.5;">
        Please do not share verbatim exam questions. This violates your exam agreement.
        We only ask about topic themes, not question content.
      </p>
    </div>
    <a href="{survey_url}"
       style="display:inline-block;background:#c0392b;color:#fff;text-decoration:none;
              font-family:'Syne',sans-serif;font-weight:700;font-size:14px;
              padding:13px 28px;border-radius:6px;margin-bottom:24px;">
      Share my outcome →
    </a>
    <p style="color:#8a8278;font-size:11px;margin:0;">
      MedMind AI · <a href="{unsubscribe_url}" style="color:#8a8278;">Don't ask me again</a>
    </p>
  </div>
</body></html>"""
    text = (
        f"Hi {name},\n\nHow did your {exam_label} exam go? Share your experience (2 min):\n{survey_url}\n\n"
        "IMPORTANT: Do not share verbatim exam questions — we only ask about topic themes.\n\n"
        f"Opt out: {unsubscribe_url}\n\nMedMind AI"
    )

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(_send_smtp, to_email, subject, html, text))
            logger.info("Exam survey email sent to %s (exam=%s reminder=%d)", to_email, exam_slug, reminder_number)
        except Exception as e:
            logger.error("Failed to send exam survey to %s: %s", to_email, e)
    else:
        logger.info("DEV MODE — exam survey for %s: %s reminder #%d", to_email, exam_slug, reminder_number)
