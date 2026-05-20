"""Job-Tracker Flask app — CRUD over Azure MySQL `JobsData` table."""
import os
import json
import calendar
from functools import wraps
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from dotenv import load_dotenv

from db import query
from reminders import start_scheduler, send_reminders_now

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-in-prod")
app.permanent_session_lifetime = timedelta(days=30)

APP_PASSWORD = os.getenv("APP_PASSWORD")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper

FIELDS = [
    "date_applied", "job_title", "job_type", "job_site", "location",
    "post_status", "company", "day_3", "day_5", "day_7",
    "hiring_manager", "company_email", "call_yn",
    "rejection_date", "interview_date",
]

STATUS_OPTIONS = [
    "Applied", "Application Viewed", "Pending Response",
    "Interviewed", "Rejected", "Offer", "Job Closed",
]

JOB_TYPE_OPTIONS = [
    "Remote", "Hybrid", "On-site", "On-site / Hybrid",
    "Contracts", "Maternity Cover",
]


def _clean(form):
    return {k: (form.get(k).strip() if form.get(k) and form.get(k).strip() else None)
            for k in FIELDS}


# ---------- Auth ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if APP_PASSWORD and request.form.get("password") == APP_PASSWORD:
            session.permanent = True
            session["logged_in"] = True
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        flash("Incorrect password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


# ---------- Routes ----------

@app.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    sql = "SELECT * FROM JobsData WHERE 1=1"
    params = []
    if q:
        sql += " AND (job_title LIKE %s OR company LIKE %s OR location LIKE %s)"
        like = f"%{q}%"
        params += [like, like, like]
    if status:
        sql += " AND post_status = %s"
        params.append(status)
    sql += " ORDER BY date_applied DESC, id DESC"
    rows = query(sql, params)
    return render_template("index.html", rows=rows, q=q, status=status, statuses=STATUS_OPTIONS)


@app.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        data = _clean(request.form)
        cols = ", ".join(f"`{k}`" for k in FIELDS)
        placeholders = ", ".join(["%s"] * len(FIELDS))
        query(f"INSERT INTO JobsData ({cols}) VALUES ({placeholders})",
              [data[k] for k in FIELDS], fetch=False)
        flash("Application added.", "success")
        return redirect(url_for("index"))
    return render_template("form.html", row=None, action="New Application",
                           statuses=STATUS_OPTIONS, job_types=JOB_TYPE_OPTIONS)


@app.route("/edit/<int:row_id>", methods=["GET", "POST"])
@login_required
def edit(row_id):
    if request.method == "POST":
        data = _clean(request.form)
        set_clause = ", ".join(f"`{k}` = %s" for k in FIELDS)
        params = [data[k] for k in FIELDS] + [row_id]
        query(f"UPDATE JobsData SET {set_clause} WHERE id = %s", params, fetch=False)
        flash("Application updated.", "success")
        return redirect(url_for("index"))
    rows = query("SELECT * FROM JobsData WHERE id = %s", [row_id])
    if not rows:
        flash("Record not found.", "error")
        return redirect(url_for("index"))
    return render_template("form.html", row=rows[0], action="Edit Application",
                           statuses=STATUS_OPTIONS, job_types=JOB_TYPE_OPTIONS)


@app.route("/delete/<int:row_id>", methods=["POST"])
@login_required
def delete(row_id):
    query("DELETE FROM JobsData WHERE id = %s", [row_id], fetch=False)
    flash("Application deleted.", "success")
    return redirect(url_for("index"))


@app.route("/send-reminders", methods=["POST"])
@login_required
def trigger_reminders():
    count = send_reminders_now()
    flash(f"Reminder email sent. {count} follow-up item(s) included.", "success")
    return redirect(url_for("index"))


# ---------- Dashboard ----------

def _delta(change, pct):
    """Return dict with pre-computed display values — no logic needed in template."""
    if change > 0:
        css = "pos"
        sign = "+"
    elif change < 0:
        css = "neg"
        sign = ""
    else:
        css = ""
        sign = ""

    if pct is None:
        badge_css = "badge-grey"
        badge_txt = "N/A"
        arrow = ""
        pct_str = "—"
    elif pct > 0:
        badge_css = "badge-green"
        badge_txt = f"▲ {abs(round(pct, 2))}%"
        arrow = "+"
        pct_str = f"+{round(pct, 2)}"
    elif pct < 0:
        badge_css = "badge-red"
        badge_txt = f"▼ {abs(round(pct, 2))}%"
        arrow = ""
        pct_str = str(round(pct, 2))
    else:
        badge_css = "badge-grey"
        badge_txt = "0%"
        arrow = ""
        pct_str = "0"

    return {
        "change": change,
        "sign": sign,
        "css": css,
        "badge_css": badge_css,
        "badge_txt": badge_txt,
        "pct_str": pct_str,
    }


@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun',
                   'Jul','Aug','Sep','Oct','Nov','Dec']

    this_week_start = today - timedelta(days=today.weekday())
    this_week_end   = this_week_start + timedelta(days=6)
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end   = this_week_start - timedelta(days=1)

    def scalar(sql, params=None):
        rows = query(sql, params)
        if rows:
            return list(rows[0].values())[0] or 0
        return 0

    total_apps       = scalar("SELECT COUNT(*) FROM JobsData")
    total_rejections = scalar("SELECT COUNT(*) FROM JobsData WHERE post_status = 'Rejected'")
    this_year        = scalar("SELECT COUNT(*) FROM JobsData WHERE YEAR(date_applied) = %s", [today.year])
    last_year        = scalar("SELECT COUNT(*) FROM JobsData WHERE YEAR(date_applied) = %s", [today.year - 1])

    this_month = scalar(
        "SELECT COUNT(*) FROM JobsData WHERE YEAR(date_applied)=%s AND MONTH(date_applied)=%s",
        [today.year, today.month])
    lm_year, lm_month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    last_month = scalar(
        "SELECT COUNT(*) FROM JobsData WHERE YEAR(date_applied)=%s AND MONTH(date_applied)=%s",
        [lm_year, lm_month])

    this_week = scalar(
        "SELECT COUNT(*) FROM JobsData WHERE date_applied BETWEEN %s AND %s",
        [this_week_start, this_week_end])
    last_week = scalar(
        "SELECT COUNT(*) FROM JobsData WHERE date_applied BETWEEN %s AND %s",
        [last_week_start, last_week_end])

    mom_change = this_month - last_month
    mom_pct    = round((mom_change / last_month * 100), 2) if last_month else None
    wow_change = this_week - last_week
    wow_pct    = round((wow_change / last_week * 100), 2) if last_week else None

    rejection_rate = f"{round(total_rejections / total_apps * 100)}%" if total_apps else "N/A"

    return render_template(
        "dashboard.html",
        today_str=today.strftime('%A, %d %B %Y'),
        this_week_str=f"{this_week_start.strftime('%d %b')} – {this_week_end.strftime('%d %b %Y')}",
        last_week_str=f"{last_week_start.strftime('%d %b')} – {last_week_end.strftime('%d %b %Y')}",
        this_month_str=f"{MONTH_NAMES[today.month - 1]} {today.year}",
        last_month_str=f"{MONTH_NAMES[lm_month - 1]} {lm_year}",
        this_year_str=str(today.year),
        last_year_str=str(today.year - 1),
        total_apps=total_apps,
        total_rejections=total_rejections,
        rejection_rate=rejection_rate,
        this_year=this_year,
        last_year=last_year,
        last_year_empty=last_year == 0,
        this_month=this_month,
        last_month=last_month,
        this_week=this_week,
        last_week=last_week,
        mom=_delta(mom_change, mom_pct),
        wow=_delta(wow_change, wow_pct),
    )


# ---------- Entry point ----------

if __name__ == "__main__":
    start_scheduler()
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
