import os
from datetime import datetime, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, send_file, session, url_for

import db
import report as rpt

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

# Initialise DB table on startup (safe to call repeatedly thanks to IF NOT EXISTS)
try:
    db.init_db()
except Exception as exc:
    print(f"Warning: could not initialise database: {exc}")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Week helpers
# ---------------------------------------------------------------------------

def parse_week(week_str: str):
    """Return (week_start, week_end) as date objects for an ISO week string like '2026-W18'."""
    week_start = datetime.strptime(f"{week_str}-1", "%G-W%V-%u").date()
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def adjacent_weeks(week_str: str):
    week_start, _ = parse_week(week_str)
    prev_str = (week_start - timedelta(weeks=1)).strftime("%G-W%V")
    next_str = (week_start + timedelta(weeks=1)).strftime("%G-W%V")
    return prev_str, next_str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == os.environ.get("APP_PASSWORD", ""):
            session["authed"] = True
            return redirect(url_for("index"))
        error = "Incorrect password — please try again."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@require_auth
def index():
    week_str = datetime.now().strftime("%G-W%V")
    return redirect(url_for("week_view", week_str=week_str))


@app.route("/week/<week_str>")
@require_auth
def week_view(week_str):
    try:
        week_start, week_end = parse_week(week_str)
    except ValueError:
        return redirect(url_for("index"))

    entries = db.get_entries_for_week(week_start, week_end)

    # Build an ordered dict: date -> list of entries
    days = {}
    for i in range(7):
        days[week_start + timedelta(days=i)] = []
    for entry in entries:
        days[entry["entry_date"]].append(entry)

    prev_week, next_week = adjacent_weeks(week_str)
    total_hours = sum(e["hours"] for e in entries)

    return render_template(
        "week.html",
        week_str=week_str,
        week_start=week_start,
        week_end=week_end,
        days=days,
        prev_week=prev_week,
        next_week=next_week,
        total_hours=total_hours,
    )


@app.route("/entry/add", methods=["POST"])
@require_auth
def add_entry():
    entry_date = request.form.get("entry_date")
    hours = request.form.get("hours")
    description = (request.form.get("description") or "").strip()
    week_str = request.form.get("week_str", "")

    if entry_date and hours and description:
        try:
            db.add_entry(entry_date, float(hours), description)
        except Exception as exc:
            print(f"add_entry error: {exc}")

    return redirect(url_for("week_view", week_str=week_str))


@app.route("/entry/delete/<int:entry_id>", methods=["POST"])
@require_auth
def delete_entry(entry_id):
    week_str = request.form.get("week_str", "")
    db.delete_entry(entry_id)
    return redirect(url_for("week_view", week_str=week_str))


@app.route("/report/<week_str>")
@require_auth
def generate_report(week_str):
    try:
        week_start, week_end = parse_week(week_str)
    except ValueError:
        return redirect(url_for("index"))

    entries = db.get_entries_for_week(week_start, week_end)
    doc_bytes = rpt.build_report(week_start, week_end, entries)

    filename = f"time_report_{week_str}.docx"
    return send_file(
        doc_bytes,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    app.run(debug=True)
