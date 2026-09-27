"""
routes/savings_routes.py – Savings account and transaction routes.
"""
from flask import Blueprint, request, jsonify, g
from db import get_db
from datetime import datetime, timezone
import bson

savings_bp = Blueprint("savings", __name__)


def _serialize_account(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if "created_at" in doc and isinstance(doc["created_at"], datetime):
        from datetime import timedelta
        sl_tz = timezone(timedelta(hours=5, minutes=30))
        dt = doc["created_at"]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        doc["created_at"] = dt.astimezone(sl_tz).strftime("%Y-%m-%d %H:%M:%S")
    return doc


def _serialize_tx(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if "created_at" in doc and isinstance(doc["created_at"], datetime):
        from datetime import timedelta
        sl_tz = timezone(timedelta(hours=5, minutes=30))
        dt = doc["created_at"]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        doc["created_at"] = dt.astimezone(sl_tz).strftime("%Y-%m-%d %H:%M:%S")
    return doc


@savings_bp.route("/api/clients/nic/<nic>", methods=["GET"])
def get_client_by_nic(nic):
    db = get_db()
    client = db.clients.find_one({"nic": nic.upper().strip(), "is_active": True})
    if not client:
        return jsonify({"success": False, "message": "Client not found with this NIC."}), 404
    
    first_name = client.get("first_name") or ""
    last_name = client.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip() or client.get("full_name", "")
    
    return jsonify({
        "success": True,
        "client": {
            "nic": client["nic"],
            "name": full_name,
            "branch": client.get("branch") or "ANAMADUWA",
            "contact": client.get("contact") or client.get("mobile_no") or ""
        }
    }), 200


@savings_bp.route("/api/savings/accounts", methods=["POST"])
def create_savings_account():
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    
    # Required validation
    required = ["nic", "client_name", "saving_product", "account_no", "branch"]
    for field in required:
        if not data.get(field):
            return jsonify({"success": False, "message": f"'{field}' is required."}), 400

    account_no = data["account_no"].strip()
    
    # Check uniqueness
    if db.savings_accounts.find_one({"account_no": account_no}):
        return jsonify({"success": False, "message": f"Account number '{account_no}' already exists."}), 409

    # Create account document
    creator = g.current_user.get("username") if hasattr(g, "current_user") and g.current_user else "admin"
    
    doc = {
        "nic": data["nic"].upper().strip(),
        "client_name": data["client_name"].strip(),
        "saving_product": data["saving_product"].strip(),
        "account_no": account_no,
        "branch": data["branch"].strip(),
        "signature": data.get("signature", ""),
        "balance": 0.0,
        "status": "Active",
        "created_at": datetime.now(timezone.utc),
        "created_by": creator
    }
    
    result = db.savings_accounts.insert_one(doc)
    return jsonify({"success": True, "id": str(result.inserted_id), "account_no": account_no}), 201


@savings_bp.route("/api/savings/accounts", methods=["GET"])
def list_savings_accounts():
    db = get_db()
    branch = request.args.get("branch", "").strip()
    product = request.args.get("product", "").strip()
    keyword = request.args.get("keyword", "").strip()

    query = {}
    if branch and branch != "--all--" and branch != "-- All --" and branch != "-- Select Branch --":
        query["branch"] = branch
    if product and product != "--all--" and product != "-- All --" and product != "-- Product --" and product != "--- Product ---":
        query["saving_product"] = product
        
    if keyword:
        query["$or"] = [
            {"account_no": {"$regex": keyword, "$options": "i"}},
            {"client_name": {"$regex": keyword, "$options": "i"}},
            {"nic": {"$regex": keyword, "$options": "i"}}
        ]

    accounts = [_serialize_account(a) for a in db.savings_accounts.find(query).sort("created_at", -1)]
    return jsonify({"success": True, "accounts": accounts}), 200


@savings_bp.route("/api/savings/transactions", methods=["POST"])
def post_transaction():
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    
    # Required validation
    required = ["account_no", "type", "amount"]
    for field in required:
        if not data.get(field):
            return jsonify({"success": False, "message": f"'{field}' is required."}), 400

    account_no = data["account_no"].strip()
    tx_type = data["type"].strip()  # Deposit or Withdrawal
    try:
        amount = float(data["amount"])
    except ValueError:
        return jsonify({"success": False, "message": "Amount must be a number."}), 400

    if amount <= 0:
        return jsonify({"success": False, "message": "Amount must be greater than zero."}), 400

    if tx_type not in ["Deposit", "Withdrawal"]:
        return jsonify({"success": False, "message": "Transaction type must be 'Deposit' or 'Withdrawal'."}), 400

    # Retrieve account details
    account = db.savings_accounts.find_one({"account_no": account_no})
    if not account:
        return jsonify({"success": False, "message": "Savings account not found."}), 404

    current_balance = float(account.get("balance", 0.0))

    if tx_type == "Withdrawal" and current_balance < amount:
        return jsonify({"success": False, "message": f"Insufficient balance. Current balance is LKR {current_balance:,.2f}"}), 400

    # Determine balance after transaction
    if tx_type == "Deposit":
        new_balance = current_balance + amount
        inc_amount = amount
    else:
        new_balance = current_balance - amount
        inc_amount = -amount

    # Update account balance atomatically
    db.savings_accounts.update_one(
        {"account_no": account_no},
        {"$inc": {"balance": inc_amount}}
    )

    # Save transaction record
    creator = g.current_user.get("username") if hasattr(g, "current_user") and g.current_user else "admin"
    
    tx_doc = {
        "account_no": account_no,
        "type": tx_type,
        "amount": amount,
        "balance_after": new_balance,
        "remarks": data.get("remarks", "").strip(),
        "created_at": datetime.now(timezone.utc),
        "created_by": creator
    }
    
    result = db.savings_transactions.insert_one(tx_doc)
    return jsonify({
        "success": True,
        "transaction_id": str(result.inserted_id),
        "new_balance": new_balance
    }), 201


@savings_bp.route("/api/savings/accounts/<account_no>/transactions", methods=["GET"])
def list_account_transactions(account_no):
    db = get_db()
    account = db.savings_accounts.find_one({"account_no": account_no})
    if not account:
        return jsonify({"success": False, "message": "Savings account not found."}), 404

    txs = [_serialize_tx(t) for t in db.savings_transactions.find({"account_no": account_no}).sort("created_at", -1)]
    return jsonify({
        "success": True,
        "account": _serialize_account(account),
        "transactions": txs
    }), 200


@savings_bp.route("/api/savings/stats", methods=["GET"])
def get_savings_stats():
    db = get_db()
    
    # 1. Total accounts & aggregate balance
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_balance": {"$sum": "$balance"},
                "total_accounts": {"$sum": 1}
            }
        }
    ]
    summary = list(db.savings_accounts.aggregate(pipeline))
    total_balance = summary[0]["total_balance"] if summary else 0.0
    total_accounts = summary[0]["total_accounts"] if summary else 0
    
    # 2. Product-wise breakdown
    prod_pipeline = [
        {
            "$group": {
                "_id": "$saving_product",
                "balance": {"$sum": "$balance"},
                "count": {"$sum": 1}
            }
        }
    ]
    products = list(db.savings_accounts.aggregate(prod_pipeline))
    product_stats = []
    for p in products:
        product_stats.append({
            "product_name": p["_id"] or "Unknown Product",
            "balance": p["balance"],
            "count": p["count"]
        })

    # 3. Today's transactions
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tx_pipeline = [
        {"$match": {"created_at": {"$gte": today_start}}},
        {
            "$group": {
                "_id": "$type",
                "total_amount": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }
        }
    ]
    tx_today = list(db.savings_transactions.aggregate(tx_pipeline))
    
    deposits_today_amt = 0.0
    deposits_today_cnt = 0
    withdrawals_today_amt = 0.0
    withdrawals_today_cnt = 0
    
    for t in tx_today:
        if t["_id"] == "Deposit":
            deposits_today_amt = t["total_amount"]
            deposits_today_cnt = t["count"]
        elif t["_id"] == "Withdrawal":
            withdrawals_today_amt = t["total_amount"]
            withdrawals_today_cnt = t["count"]

    # 4. Recent Accounts created
    recent_accounts = [_serialize_account(a) for a in db.savings_accounts.find().sort("created_at", -1).limit(5)]
    
    return jsonify({
        "success": True,
        "stats": {
            "total_balance": total_balance,
            "total_accounts": total_accounts,
            "deposits_today_amount": deposits_today_amt,
            "deposits_today_count": deposits_today_cnt,
            "withdrawals_today_amount": withdrawals_today_amt,
            "withdrawals_today_count": withdrawals_today_cnt,
            "products": product_stats,
            "recent_accounts": recent_accounts
        }
    }), 200
