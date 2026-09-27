"""models/payments.py – Payment and Settlement document helpers."""
from datetime import datetime, timezone


def new_payment(
    loan_id: str,
    amount: float,
    payment_type: str = "Group",
    collected_by: str = None,
) -> dict:
    return {
        "loan_id": loan_id,
        "amount": amount,
        "payment_type": payment_type,   # "Group" | "Individual" | "Collection"
        "collected_by": collected_by,
        "payment_date": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }


def new_settlement(loan_id: str, amount: float, officer: str = None) -> dict:
    return {
        "loan_id": loan_id,
        "amount": amount,
        "officer": officer,
        "settled_date": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
