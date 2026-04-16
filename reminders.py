"""Daily email reminders for Day 3 / 5 / 7 follow-ups.

Logic: for each application whose `date_applied` was exactly 3, 5, or 7
days ago AND whose status is still 'open' (not Rejected / Job Closed /
Interviewed / Offer), add it to a single digest email sent once per day.
"""
import os
import smtplib
from datetime import date, timedelta
from email.message import EmailMessage

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from db import query

load_dotenv()

OPEN_STATUSES = ("Applied", "Application Viewed", "Pending Response")


def _find_due_applications():
    """Return list of (day_number, row) tuples for due follow-ups."""
    today = date.today()
    results = []
    for days in (3, 5, 7):
        target = today - timedelta(days=days)
        rows = query(
            "SELECT * FROM JobsData "
            "WHERE date_applied = %s "
            "AND post_status IN (%s, %s, %s)",
            [target, *OPEN_STATUSES],
        )
        for r in rows:
            results.append((days, r))
    return results


def _build_email_body(items):
    if not items:
        return "No follow-ups due today. Nothing to chase."

    lines = ["Job-Tracker follow-up digest", "=" * 40, ""]
    by_day = {3: [], 5: [], 7: []}
    for days, row in items:
        by_day[days].append(row)

    for days in (3, 5, 7):
        rows = by_day[days]
        if not rows:
            continue
        lines.append(f"--- Day {days} follow-ups ({len(rows)}) ---")
        for r in rows:
            company = r.get("company") or "(no company)"
            title = r.get("job_title") or "(no title)"
            site = r.get("job_site") or "?"
            applied = r.get("date_applied")
            lines.append(f"  #{r['id']}  {title}  @ {company}")
            lines.append(f"           via {site} on {applied} — status: {r.get('post_status')}")
        lines.append("")

    lines.append("Open the tracker to update statuses.")
    return "\n".join(lines)


def send_reminders_now():
    """Send the digest email immediately. Returns count of items included."""
    items = _find_due_applications()
    body = _build_email_body(items)

    msg = EmailMessage()
    msg["Subject"] = f"Job-Tracker: {len(items)} follow-up(s) due"
    msg["From"] = os.getenv("EMAIL_FROM")
    msg["To"] = os.getenv("EMAIL_TO")
    msg.set_content(body)

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)

    print(f"[reminders] Sent email with {len(items)} item(s).")
    return len(items)


def start_scheduler():
    """Start the daily reminder job in the background."""
    hour = int(os.getenv("REMINDER_HOUR", "9"))
    minute = int(os.getenv("REMINDER_MINUTE", "0"))

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        send_reminders_now,
        trigger="cron",
        hour=hour,
        minute=minute,
        id="daily_reminders",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[reminders] Scheduler started — daily at {hour:02d}:{minute:02d}")
    return scheduler
