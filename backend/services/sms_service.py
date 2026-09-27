"""
services/sms_service.py – SMSlenz.lk SMS Integration Service.

Handles phone number normalization, message templating, and asynchronous
SMS dispatch for Central Credit repayments.
"""
import os
import re
import json
import urllib.request
import urllib.error
import threading
from datetime import datetime
from bson import ObjectId

# Default SMSlenz Credentials
DEFAULT_USER_ID = "2173"
DEFAULT_API_KEY = "39192d1c-a7c2-40c9-9f7d-3d00eee5ad16"
DEFAULT_SENDER_ID = "KarandeniInv"
DEFAULT_API_URL = "https://smslenz.lk/api/send-sms"


def get_sms_config():
    return {
        "user_id": os.getenv("SMSLENZ_USER_ID", DEFAULT_USER_ID).strip(),
        "api_key": os.getenv("SMSLENZ_API_KEY", DEFAULT_API_KEY).strip(),
        "sender_id": os.getenv("SMSLENZ_SENDER_ID", DEFAULT_SENDER_ID).strip(),
        "api_url": os.getenv("SMSLENZ_API_URL", DEFAULT_API_URL).strip(),
    }


def normalize_phone_number(phone_raw: str) -> str:
    """
    Normalizes Sri Lankan phone numbers to the international +947XXXXXXXX format.
    Supports formats like:
      - 0771234567 -> +94771234567
      - 771234567  -> +94771234567
      - 94771234567 -> +94771234567
      - +94771234567 -> +94771234567
    """
    if not phone_raw:
        return ""
    
    # Strip spaces, hyphens, brackets
    cleaned = re.sub(r"[\s\-\(\)]", "", str(phone_raw).strip())
    
    # +947XXXXXXXX (12 chars)
    if re.match(r"^\+947\d{8}$", cleaned):
        return cleaned
    
    # 947XXXXXXXX (11 digits)
    if re.match(r"^947\d{8}$", cleaned):
        return f"+{cleaned}"
    
    # 07XXXXXXXX (10 digits)
    if re.match(r"^07\d{8}$", cleaned):
        return f"+94{cleaned[1:]}"
    
    # 7XXXXXXXX (9 digits)
    if re.match(r"^7\d{8}$", cleaned):
        return f"+94{cleaned}"
    
    # Fallback: if starts with +, return cleaned, else return raw
    if cleaned.startswith("+"):
        return cleaned
    return cleaned


def build_repayment_message(title: str, name: str, payment_amount: float, outstanding_balance: float) -> str:
    """
    Constructs the repayment SMS template:
    Dear {Title} . {LAST_NAME}, your loan recorded a repayment of Rs. {Amount}. The current outstanding balance is Rs. {Outstanding_Balance}.
    Thank you for your payment.
    """
    title_clean = (title or "").strip()
    if not title_clean:
        title_clean = "Mr/Mrs"
    
    name_clean = (name or "Customer").strip().upper()
    
    amt_formatted = f"{float(payment_amount):,.2f}"
    bal_formatted = f"{float(outstanding_balance):,.2f}"
    
    message = (
        f"Dear {title_clean} . {name_clean}, your loan recorded a repayment of Rs. {amt_formatted}. "
        f"The current outstanding balance is Rs. {bal_formatted}.\n"
        f"Thank you for your payment."
    )
    return message


def send_sms(contact: str, message: str) -> dict:
    """
    Sends a single SMS via SMSlenz.lk HTTP POST API.
    """
    normalized_contact = normalize_phone_number(contact)
    if not normalized_contact:
        print(f"[SMSlenz] Skipping SMS: Invalid or empty contact '{contact}'")
        return {"success": False, "error": "Invalid phone number"}

    config = get_sms_config()
    payload = {
        "user_id": str(config["user_id"]),
        "api_key": str(config["api_key"]),
        "sender_id": str(config["sender_id"]),
        "contact": normalized_contact,
        "message": message,
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        config["api_url"],
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "KarandeniInvestment-Core/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            resp_body = response.read().decode("utf-8")
            try:
                resp_json = json.loads(resp_body)
            except Exception:
                resp_json = {"raw": resp_body}
            print(f"[SMSlenz] SMS dispatched successfully to {normalized_contact}: {resp_json}")
            return {"success": True, "response": resp_json}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"[SMSlenz] HTTP Error {e.code} sending SMS to {normalized_contact}: {err_body}")
        return {"success": False, "error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        print(f"[SMSlenz] Network error sending SMS to {normalized_contact}: {e}")
        return {"success": False, "error": str(e)}


def send_sms_async(contact: str, message: str):
    """
    Dispatches SMS in a separate background daemon thread to ensure zero latency on UI responses.
    """
    thread = threading.Thread(
        target=send_sms,
        args=(contact, message),
        daemon=True
    )
    thread.start()


def trigger_loan_repayment_sms(db, loan_id_val, repayment_amount: float):
    """
    Calculates loan balance and dispatches SMS for a loan repayment.
    """
    try:
        # 1. Fetch loan
        loan = None
        try:
            loan = db.loans.find_one({"_id": ObjectId(str(loan_id_val))})
        except Exception:
            pass
        if not loan:
            loan = db.loans.find_one({"_id": str(loan_id_val)})
        if not loan:
            loan = db.loans.find_one({"loan_no": str(loan_id_val)})
            
        if not loan:
            print(f"[SMSlenz] Cannot send SMS: Loan not found for ID '{loan_id_val}'")
            return

        # 2. Fetch client
        client = None
        client_id = loan.get("client_id")
        if client_id:
            try:
                client = db.clients.find_one({"_id": ObjectId(str(client_id))})
            except Exception:
                pass
            if not client:
                client = db.clients.find_one({"_id": str(client_id)})
            if not client:
                client = db.clients.find_one({"nic": str(client_id)})
                
        if not client:
            print(f"[SMSlenz] Cannot send SMS: Client not found for loan ID '{loan_id_val}'")
            return

        # 3. Extract contact phone
        phone = client.get("mobile_no") or client.get("contact") or client.get("land_phone")
        if not phone:
            print(f"[SMSlenz] Client '{client.get('nic')}' has no phone number on record.")
            return

        # 4. Calculate full agreed payback and outstanding balance
        amount = float(loan.get("amount", 0.0))
        tenor = int(loan.get("tenor") or 24)
        payback = amount + (amount * 0.0155 * tenor)
        if amount == 10000 and tenor == 13:
            payback = 12600.0
        elif amount == 15000 and tenor == 13:
            payback = 19000.0

        # Query all payments to calculate updated paid_amount
        actual_loan_id = loan.get("_id")
        payments = list(db.payments.find({"$or": [{"loan_id": str(actual_loan_id)}, {"loan_id": actual_loan_id}]}))
        total_paid = sum(float(p.get("amount", 0.0)) for p in payments)
        outstanding = max(0.0, payback - total_paid)

        # 5. Extract Title and Name
        title = client.get("title")
        if not title:
            gender = str(client.get("gender") or "").lower()
            title = "Mrs" if gender in ["female", "f"] else "Mr"

        # Determine last name / name
        last_name = client.get("last_name")
        if not last_name:
            full_name = client.get("full_name") or ""
            name_parts = full_name.strip().split()
            last_name = name_parts[-1] if name_parts else (client.get("first_name") or "Customer")

        # 6. Build message text
        msg_text = build_repayment_message(
            title=title,
            name=last_name,
            payment_amount=repayment_amount,
            outstanding_balance=outstanding
        )

        print(f"[SMSlenz] Triggering repayment SMS for {client.get('nic')} ({phone}):\n{msg_text}")
        
        # 7. Dispatch asynchronously
        send_sms_async(phone, msg_text)

    except Exception as e:
        print(f"[SMSlenz] Error preparing repayment SMS: {e}")
