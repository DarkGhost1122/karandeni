"""
auth.py – Password hashing, JWT generation and verification.
"""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION_USE_LONG_SECRET")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "1"))
JWT_ALGORITHM = "HS256"


# ── Password helpers ────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt (cost factor 12)."""
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def check_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT helpers ─────────────────────────────────────────────────────────────

def generate_token(user_doc: dict) -> str:
    """
    Create a signed JWT for the given user document.
    Payload includes user_id, username, display_name, role, and expiry.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_doc["_id"]),
        "username": user_doc["username"],
        "display_name": user_doc.get("display_name", user_doc["username"].upper()),
        "role": user_doc.get("role", "user"),
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """
    Decode and verify a JWT.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    Returns the decoded payload dict on success.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
