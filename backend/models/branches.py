"""models/branches.py – Branch document helpers."""
from datetime import datetime, timezone


def new_branch(name: str, code: str) -> dict:
    return {
        "name": name.strip().upper(),
        "code": code.strip().upper(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
