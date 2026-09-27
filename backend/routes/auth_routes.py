"""
routes/auth_routes.py – Login / logout endpoints.

POST /api/login   → { success, token, display_name }
POST /api/logout  → { success }  (stateless – client drops the token)
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from db import get_db
from auth import check_password, generate_token

auth_bp = Blueprint("auth", __name__)

# Simple in-memory rate limiter: { ip: [timestamp, ...] }
_login_attempts: dict = {}
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60


def _is_rate_limited(ip: str) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    attempts = _login_attempts.get(ip, [])
    # keep only attempts within the window
    attempts = [t for t in attempts if now - t < WINDOW_SECONDS]
    _login_attempts[ip] = attempts
    if len(attempts) >= MAX_ATTEMPTS:
        return True
    attempts.append(now)
    _login_attempts[ip] = attempts
    return False


@auth_bp.route("/api/login", methods=["POST"])
def login():
    ip = request.remote_addr or "unknown"
    if _is_rate_limited(ip):
        return jsonify({"success": False, "message": "Too many login attempts. Please wait 1 minute."}), 429

    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").lower().strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."}), 400

    db = get_db()
    user = db.users.find_one({"username": username, "is_active": True})

    if not user or not check_password(password, user["password_hash"]):
        return jsonify({"success": False, "message": "Invalid username or password."}), 401

    # Update last_login timestamp
    db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc)}})

    token = generate_token(user)
    return jsonify({
        "success": True,
        "token": token,
        "display_name": user.get("display_name", username.upper()),
        "role": user.get("role", "user"),
    }), 200


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    # Stateless – the client simply discards the token.
    return jsonify({"success": True}), 200
