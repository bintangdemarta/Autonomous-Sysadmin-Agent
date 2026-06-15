from __future__ import annotations

from functools import wraps
from pathlib import Path
import secrets
import sys
import time

from flask import Flask, Response, jsonify, render_template, request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nexus.config import ConfigError, get_web_auth_credentials, load_commands, save_commands
from nexus.runner import run_user_command

app = Flask(__name__)

# In-memory display cache for the web UI; authoritative audit logs are written to data/audit_log.jsonl.
command_history = []


def _auth_configured() -> bool:
    username, password = get_web_auth_credentials()
    return bool(username and password)


def _is_authorized() -> bool:
    expected_username, expected_password = get_web_auth_credentials()
    if not expected_username or not expected_password:
        return True

    auth = request.authorization
    if not auth:
        return False
    return secrets.compare_digest(auth.username, expected_username) and secrets.compare_digest(
        auth.password, expected_password
    )


def require_auth(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if _is_authorized():
            return view_func(*args, **kwargs)
        return Response(
            "Authentication required",
            401,
            {"WWW-Authenticate": 'Basic realm="Nexus-CLI"'},
        )

    return wrapper


@app.route("/")
@require_auth
def index():
    """Main dashboard page"""
    return render_template("index.html", auth_configured=_auth_configured())


@app.route("/dashboard")
@require_auth
def dashboard():
    """Dashboard with system info"""
    return render_template("index.html", auth_configured=_auth_configured())


@app.route("/commands")
@require_auth
def commands():
    """Page to manage commands"""
    return render_template("commands.html", auth_configured=_auth_configured())


@app.route("/execute", methods=["POST"])
@require_auth
def execute_command():
    """Execute a command via Nexus-CLI."""
    payload = request.get_json(silent=True) or {}
    user_input = payload.get("command", "")
    confirmed = bool(payload.get("confirmed", False))

    if not user_input.strip():
        return jsonify({"success": False, "error": "Command cannot be empty"}), 400

    result = run_user_command(user_input, confirmed=confirmed, actor="web")

    command_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "input": user_input,
        "output": result.get("output", ""),
        "success": result.get("success", False),
        "parsed_command": result.get("parsed_command"),
        "risk_level": result.get("risk_level"),
    }
    command_history.insert(0, command_entry)

    if len(command_history) > 50:
        command_history[:] = command_history[:50]

    return jsonify(result)


@app.route("/history")
@require_auth
def get_history():
    """Get command execution history."""
    return jsonify(command_history)


@app.route("/history/clear", methods=["POST"])
@require_auth
def clear_history():
    """Clear command execution history display cache."""
    command_history.clear()
    return jsonify({"success": True, "message": "History cleared successfully"})


@app.route("/config", methods=["GET", "POST"])
@require_auth
def manage_config():
    """Manage command configuration."""
    if request.method == "POST":
        try:
            new_config = request.get_json(silent=True)
            save_commands(new_config)
            return jsonify({"success": True, "message": "Configuration updated successfully"})
        except ConfigError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400
        except Exception as exc:  # noqa: BLE001 - user-facing API should report unexpected failures.
            return jsonify({"success": False, "error": str(exc)}), 500

    try:
        return jsonify(load_commands())
    except ConfigError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
