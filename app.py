"""Job-Tracker Flask app — CRUD over Azure MySQL `JobsData` table."""
import os
from functools import wraps
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from dotenv import load_dotenv

from db import query
from reminders import start_scheduler, send_reminders_now

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-in-prod")
app.permanent_session_lifetime = timedelta(days=30)  # stay logged in for 30 days

APP_PASSWORD = os.getenv("APP_PASSWORD")


def login_required(f):
    """Protect routes — redirect to /login if not authenticated."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper

# Columns the form submits (id is auto, so excluded)
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
    """Convert empty strings to None so MySQL stores NULL, not ''."""
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
    return render_template(
        "index.html", rows=rows, q=q, status=status,
        statuses=STATUS_OPTIONS,
    )


@app.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        data = _clean(request.form)
        cols = ", ".join(f"`{k}`" for k in FIELDS)
        placeholders = ", ".join(["%s"] * len(FIELDS))
        query(
            f"INSERT INTO JobsData ({cols}) VALUES ({placeholders})",
            [data[k] for k in FIELDS],
            fetch=False,
        )
        flash("Application added.", "success")
        return redirect(url_for("index"))

    return render_template(
        "form.html", row=None, action="New Application",
        statuses=STATUS_OPTIONS, job_types=JOB_TYPE_OPTIONS,
    )


@app.route("/edit/<int:row_id>", methods=["GET", "POST"])
@login_required
def edit(row_id):
    if request.method == "POST":
        data = _clean(request.form)
        set_clause = ", ".join(f"`{k}` = %s" for k in FIELDS)
        params = [data[k] for k in FIELDS] + [row_id]
        query(
            f"UPDATE JobsData SET {set_clause} WHERE id = %s",
            params,
            fetch=False,
        )
        flash("Application updated.", "success")
        return redirect(url_for("index"))

    rows = query("SELECT * FROM JobsData WHERE id = %s", [row_id])
    if not rows:
        flash("Record not found.", "error")
        return redirect(url_for("index"))

    return render_template(
        "form.html", row=rows[0], action="Edit Application",
        statuses=STATUS_OPTIONS, job_types=JOB_TYPE_OPTIONS,
    )


@app.route("/delete/<int:row_id>", methods=["POST"])
@login_required
def delete(row_id):
    query("DELETE FROM JobsData WHERE id = %s", [row_id], fetch=False)
    flash("Application deleted.", "success")
    return redirect(url_for("index"))


@app.route("/send-reminders", methods=["POST"])
@login_required
def trigger_reminders():
    """Manually fire the reminder email (useful for testing)."""
    count = send_reminders_now()
    flash(f"Reminder email sent. {count} follow-up item(s) included.", "success")
    return redirect(url_for("index"))


# ---------- Entry point ----------

if __name__ == "__main__":
    start_scheduler()  # background job for daily reminders
    port = int(os.getenv("FLASK_PORT", "5000"))
    # host=0.0.0.0 so it's reachable from your phone on the same Wi-Fi
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
