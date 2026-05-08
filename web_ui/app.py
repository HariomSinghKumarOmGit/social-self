# Module: web_ui_app | Purpose: Flask calendar dashboard and account management APIs.
# Public API: app

from __future__ import annotations

import os
import sys

# Ensure the project root is on the Python path so sibling modules are importable.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from database import (
    add_managed_account,
    delete_managed_account,
    get_managed_accounts,
    get_posts_feed,
    get_preferences,
    get_time_slots,
    get_scheduled,
    mark_posted,
    reject_post,
    reschedule_post,
    schedule_post,
    set_default_time,
    set_target_account,
)

app = Flask(__name__)
CORS(app)


@app.get("/")
def index() -> str:
    """Render dashboard UI."""
    return render_template("calendar.html")


@app.get("/feed")
def feed() -> str:
    """Render scraped posts feed UI."""
    return render_template("feed.html")


@app.get("/api/scheduled")
def api_scheduled() -> Any:
    """Return all approved scheduled posts."""
    return jsonify(get_scheduled())


@app.get("/api/posts/feed")
def api_posts_feed() -> Any:
    """Return all posts for the feed UI."""
    return jsonify(get_posts_feed())


@app.post("/api/posts/reject")
def api_posts_reject() -> Any:
    """Reject a pending post."""
    body = request.get_json(force=True, silent=True) or {}
    post_id = int(body.get("post_id", 0) or 0)
    ok = reject_post(post_id) if post_id > 0 else False
    return jsonify({"ok": ok})


@app.post("/api/posts/schedule")
def api_posts_schedule() -> Any:
    """Schedule a post for a date + time, also updates default time preference."""
    body = request.get_json(force=True, silent=True) or {}
    post_id = int(body.get("post_id", 0) or 0)
    date_s = str(body.get("date", "")).strip()
    time_s = str(body.get("time", "")).strip()
    if post_id <= 0 or not date_s or not time_s:
        return jsonify({"ok": False, "error": "post_id, date, time required"}), 400
    ok = schedule_post(post_id, date_s, time_s)
    if ok:
        set_default_time(time_s)
    return jsonify({"ok": ok})


@app.get("/api/preferences")
def api_preferences() -> Any:
    """Return preferences + computed time slots (default slot first)."""
    return jsonify({"preferences": get_preferences(), "time_slots": get_time_slots()})


@app.post("/api/preferences/default_time")
def api_preferences_default_time() -> Any:
    """Persist the default posting time."""
    body = request.get_json(force=True, silent=True) or {}
    time_s = str(body.get("time", "")).strip()
    if not time_s:
        return jsonify({"ok": False, "error": "time required"}), 400
    set_default_time(time_s)
    return jsonify({"ok": True})


@app.post("/api/reschedule")
def api_reschedule() -> Any:
    """Reschedule a post by updating scheduled date+time."""
    body = request.get_json(force=True, silent=True) or {}
    post_id = int(body.get("post_id", 0) or 0)
    new_time = str(body.get("new_time", "")).strip()
    new_date = str(body.get("new_date", "")).strip()
    if post_id <= 0 or not new_time:
        return jsonify({"ok": False, "error": "post_id and new_time required"}), 400
    if not new_date:
        new_date = datetime.utcnow().date().isoformat()
    ok = reschedule_post(post_id, new_date, new_time)
    if ok:
        set_default_time(new_time)
    return jsonify({"ok": ok})


@app.post("/api/post-now")
def api_post_now() -> Any:
    """Mark a scheduled post as posted (hook for poster integration)."""
    body = request.get_json(force=True, silent=True) or {}
    post_id = int(body.get("post_id", 0) or 0)
    ok = mark_posted(post_id) if post_id > 0 else False
    return jsonify({"ok": ok})


@app.get("/api/status")
def api_status() -> Any:
    """Return simple operational status summary."""
    scheduled = get_scheduled()
    return jsonify(
        {
            "ok": True,
            "now": datetime.utcnow().isoformat(),
            "scheduled_count": len(scheduled),
            "today_posted": 0,
        }
    )


@app.get("/api/accounts")
def api_accounts() -> Any:
    """Return source and posting accounts."""
    return jsonify(
        {
            "source": get_managed_accounts("source"),
            "posting": get_managed_accounts("posting"),
        }
    )


@app.post("/api/accounts/add")
def api_accounts_add() -> Any:
    """Add managed account record."""
    body = request.get_json(force=True, silent=True) or {}
    account_type = str(body.get("account_type", "")).strip().lower()
    platform = str(body.get("platform", "")).strip().lower()
    username = str(body.get("username", "")).strip()
    if account_type not in {"source", "posting"}:
        return jsonify({"ok": False, "error": "account_type must be source|posting"}), 400
    if platform not in {"instagram", "twitter", "youtube"}:
        return jsonify({"ok": False, "error": "invalid platform"}), 400
    if not username:
        return jsonify({"ok": False, "error": "username required"}), 400
    ok = add_managed_account(account_type, platform, username)
    return jsonify({"ok": ok})


@app.post("/api/accounts/delete")
def api_accounts_delete() -> Any:
    """Delete managed account by id."""
    body = request.get_json(force=True, silent=True) or {}
    account_id = int(body.get("id", 0) or 0)
    ok = delete_managed_account(account_id) if account_id > 0 else False
    return jsonify({"ok": ok})


@app.post("/api/posts/target-account")
def api_target_account() -> Any:
    """Set target posting account on a post."""
    body = request.get_json(force=True, silent=True) or {}
    post_id = int(body.get("post_id", 0) or 0)
    target_account = str(body.get("target_account", "")).strip()
    if post_id <= 0 or not target_account:
        return jsonify({"ok": False, "error": "post_id and target_account required"}), 400
    ok = set_target_account(post_id, target_account)
    return jsonify({"ok": ok})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
