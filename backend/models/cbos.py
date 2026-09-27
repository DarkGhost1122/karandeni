"""models/cbos.py – CBO (Community Banking Organisation) document helpers."""
from datetime import datetime, timezone


def new_cbo(
    name: str,
    branch_id: str,
    credit_officer: str = None,
    cbo_code: str = "001",
    meeting_day: str = "Tuesday",
    meeting_time: str = "11:00",
    cbo_leader: str = "No Leader",
) -> dict:
    return {
        "name": name.strip(),
        "branch_id": branch_id,
        "credit_officer": credit_officer,
        "cbo_code": cbo_code,
        "meeting_day": meeting_day,
        "meeting_time": meeting_time,
        "cbo_leader": cbo_leader,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
