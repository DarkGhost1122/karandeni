"""models/loans.py – Loan document helpers."""
from datetime import datetime, timezone


def new_loan(
    loan_no: str,
    branch: str,
    credit_officer: str,
    cbo: str,
    client_id: str,
    amount: float,
    loan_type: str = "Micro Finance",
    status: str = "Pending",
    product: str = None,
    tenor: int = None,
    disbursement_date=None,
) -> dict:
    parsed_disb_date = None
    if disbursement_date:
        if isinstance(disbursement_date, str):
            try:
                parsed_disb_date = datetime.strptime(disbursement_date.split("T")[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        elif isinstance(disbursement_date, datetime):
            parsed_disb_date = disbursement_date

    return {
        "loan_no": loan_no,
        "branch": branch,
        "credit_officer": credit_officer,
        "cbo": cbo,
        "client_id": client_id,
        "amount": amount,
        "loan_type": loan_type,    # "Micro Finance" | "Business" | "Customer" | "Micro Express"
        "status": status,          # "Pending" | "Approved" | "Disbursed" | "Active" | "Settled" | "Sent Back"
        "product": product,
        "tenor": tenor,
        "disbursement_date": parsed_disb_date,
        "reg_date": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
