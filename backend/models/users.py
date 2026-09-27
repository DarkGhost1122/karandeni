"""models/users.py – User document helpers."""
from datetime import datetime, timezone


def new_user(username: str, password_hash: str, display_name: str, role: str = "user") -> dict:
    return {
        "username": username.lower().strip(),
        "password_hash": password_hash,
        "display_name": display_name,
        "role": role,                    # "admin" | "cashier" | "user"
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    }
