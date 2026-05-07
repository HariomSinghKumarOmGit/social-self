# Module: web_ui_app | Purpose: Flask calendar dashboard and account management APIs.
# Public API: app

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from database import (
    add_managed_account,
    delete_managed_account,
    get_managed_accounts,
    get_scheduled,
    mark_posted,
    set_target_account,
)

app = Flask(__name__)
CORS(app)


@app.get("/")
def index() -> str:
    """Render dashboard UI."""
    return render_template("calendar.html")


@app.get("/api/scheduled")
def api_scheduled() -> Any:
    """Return all approved scheduled posts."""
    return jsonify(get_scheduled())


@app.post("/api/reschedule")
def api_reschedule() -> Any:
    """Reschedule a post by updating scheduled_time."""
    body = request.get_json(force=True, silent=True) or {}
    post_id = int(body.get("post_id", 0) or 0)
    new_time = str(body.get("new_time", "")).strip()
    if post_id <= 0 or not new_time:
        return jsonify({"ok": False, "error": "post_id and new_time required"}), 400
    from database import approve_post

    ok = approve_post(post_id, new_time)
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
    app.run(host="0.0.0.0", port=5000, debug=False)
