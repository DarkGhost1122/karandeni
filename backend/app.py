"""
app.py – MACS MF Flask application entry point.

Run:
    cd backend
    python app.py

The server starts on http://localhost:5000 by default.
Set FLASK_PORT in .env to change the port.
"""
import os
import jwt as pyjwt
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# ── Create app ────────────────────────────────────────────────────────────
app = Flask(__name__)

# Allow localhost during development, plus whatever origins are listed
# in the ALLOWED_ORIGINS env var (comma-separated) for production, e.g.
# ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-app-git-main.vercel.app
_extra_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:*",
            "http://127.0.0.1:*",
            "null",          # file:// opened pages send Origin: null
            *_extra_origins,
        ],
        "supports_credentials": True,
    }
})

# ── Register Blueprints ───────────────────────────────────────────────────
from routes.auth_routes import auth_bp
from routes.loan_routes import loan_bp
from routes.cashier_routes import cashier_bp
from routes.client_routes import client_bp
from routes.cbo_routes import cbo_bp
from routes.cbo_mgmt_routes import cbo_mgmt_bp
from routes.accounts_routes import accounts_bp
from routes.savings_routes import savings_bp

app.register_blueprint(auth_bp)
app.register_blueprint(loan_bp)
app.register_blueprint(cashier_bp)
app.register_blueprint(client_bp)
app.register_blueprint(cbo_bp)
app.register_blueprint(cbo_mgmt_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(savings_bp)

# ── Clean System Initialization / Bootstrap ──────────────────────────────
try:
    from db import get_db
    from auth import hash_password
    from datetime import datetime, timezone
    db = get_db()
    
    # Ensure default Administrator exists
    admin_uname = os.getenv("ADMIN_USERNAME", "asindu")
    admin_pwd = os.getenv("ADMIN_PASSWORD", "1234")
    admin_display = os.getenv("ADMIN_DISPLAY_NAME", "ASINDU YASITH")
    
    if not db.users.find_one({"username": admin_uname}):
        db.users.insert_one({
            "username": admin_uname,
            "password_hash": hash_password(admin_pwd),
            "display_name": admin_display,
            "role": "admin",
            "branch": "KARANDENIYA",
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        })
        print(f"  [INIT] Created default administrator '{admin_uname}'")

    # Ensure default Branch exists
    if not db.branches.find_one({"name": "KARANDENIYA"}):
        db.branches.insert_one({
            "name": "KARANDENIYA",
            "code": "KDN",
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        })
        print("  [INIT] Created default branch 'KARANDENIYA' (KDN)")
except Exception as e:
    print(f"  [INIT WARNING] {e}")

# ── JWT middleware – protect every /api/* except /api/login ───────────────
from auth import verify_token

PUBLIC_ENDPOINTS = {"/api/login", "/api/logout", "/api/health", "/api/admin/clear-database", "/api/admin/seed-test-data", "/api/admin/debug-db", "/api/admin/run-seeder"}


@app.before_request
def require_auth():
    """Verify JWT on every /api/* request except public endpoints."""
    if request.method == "OPTIONS":
        return
    path = request.path
    if not path.startswith("/api/"):
        return  # static files etc.
    if path in PUBLIC_ENDPOINTS:
        return  # no auth needed

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "Missing or invalid Authorization header."}), 401

    token = auth_header[7:]
    try:
        payload = verify_token(token)
        g.current_user = payload
    except pyjwt.ExpiredSignatureError:
        return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401
    except pyjwt.InvalidTokenError:
        return jsonify({"success": False, "message": "Invalid token."}), 401


# ── Health check ──────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Karandeni Investment API"}), 200


# ── 404 / 405 JSON handlers ───────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"success": False, "message": "Method not allowed."}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"success": False, "message": "Internal server error."}), 500


# ── Entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Hugging Face Spaces (Docker SDK) always sends traffic to port 7860 and
    # sets the PORT env var accordingly, so PORT takes priority over FLASK_PORT.
    port = int(os.getenv("PORT", os.getenv("FLASK_PORT", "5000")))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print(f"  Karandeni Investment API running on http://0.0.0.0:{port}")
    print(f"  Debug mode: {debug}")
    app.run(host="0.0.0.0", port=port, debug=debug)
