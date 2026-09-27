"""
routes/loan_routes.py – Loan Overview, All Loans, Print Agreement.

GET  /api/loans            ?branch=&credit_officer=&cbo=&loan_type=&status=&from_date=&to_date=&keyword=&loan_id=&search_by=
GET  /api/loans/<id>
POST /api/loans            create new loan
"""
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from datetime import datetime, timezone
from db import get_db
from models.loans import new_loan

loan_bp = Blueprint("loan", __name__)


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    from datetime import timedelta
    sl_tz = timezone(timedelta(hours=5, minutes=30))
    for f in ["reg_date", "disbursement_date", "created_at"]:
        if doc.get(f) and isinstance(doc[f], datetime):
            dt = doc[f]
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            doc[f] = dt.astimezone(sl_tz).strftime("%Y-%m-%d")
            
    # Enrich with client info
    db = get_db()
    client_name = ""
    client_nic = ""
    client_id = doc.get("client_id")
    if client_id:
        client_doc = None
        try:
            client_doc = db.clients.find_one({"_id": ObjectId(client_id)})
        except Exception:
            pass
        if not client_doc:
            client_doc = db.clients.find_one({"nic": client_id})
        
        if client_doc:
            client_name = client_doc.get("full_name", "")
            client_nic = client_doc.get("nic", "")
            
    doc["client_name"] = client_name
    doc["client_nic"] = client_nic

    # Calculate paid_amount dynamically and include payments history list
    payments = list(db.payments.find({"$or": [{"loan_id": doc["id"]}, {"loan_id": ObjectId(doc["id"])}]}))
    doc["paid_amount"] = sum(p.get("amount", 0.0) for p in payments)

    # Calculate financial metrics (payback, installment, arrears, outstanding)
    amount = float(doc.get("amount", 0.0))
    tenor = int(doc.get("tenor", 24))
    payback = amount + (amount * 0.0155 * tenor)
    if amount == 10000 and tenor == 13:
        payback = 12600.0
    elif amount == 15000 and tenor == 13:
        payback = 19000.0
    installment = round(payback / tenor) if tenor > 0 else 0.0

    today_dt = datetime.now(timezone.utc)
    reg_val = doc.get("disbursement_date") or doc.get("reg_date")
    reg_dt = None
    if isinstance(reg_val, datetime):
        reg_dt = reg_val
    elif isinstance(reg_val, str) and reg_val:
        try:
            reg_dt = datetime.strptime(reg_val[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            reg_dt = None
    if not reg_dt:
        reg_dt = today_dt

    if reg_dt.tzinfo is None:
        reg_dt = reg_dt.replace(tzinfo=timezone.utc)

    days_elapsed = (today_dt - reg_dt).days
    num_due = max(0, min(tenor, days_elapsed // 7)) if days_elapsed > 0 else 0
    expected_due = num_due * installment
    if num_due >= tenor:
        expected_due = payback

    status = doc.get("status", "Active")
    if status in ["Settled", "Completed"]:
        arrears = 0.0
    elif status in ["Disbursed", "Active"]:
        arrears = max(0.0, expected_due - doc["paid_amount"])
    else:
        arrears = 0.0

    doc["arrears"] = arrears
    doc["installment"] = installment
    doc["payback"] = payback
    doc["outstanding"] = max(0.0, payback - doc["paid_amount"])

    serialized_payments = []
    for p in payments:
        p_date = p.get("payment_date") or p.get("date")
        if p_date and isinstance(p_date, datetime):
            if p_date.tzinfo is None:
                p_date = p_date.replace(tzinfo=timezone.utc)
            p_date_str = p_date.astimezone(sl_tz).strftime("%Y-%m-%d %I:%M %p")
        else:
            p_date_str = str(p_date or "")
            
        serialized_payments.append({
            "id": str(p["_id"]),
            "amount": p.get("amount", 0.0),
            "payment_date": p_date_str,
            "collected_by": p.get("collected_by", "admin")
        })
    doc["payments_history"] = serialized_payments
    return doc


def _build_query(args) -> dict:
    query = {}
    branch = args.get("branch", "").strip()
    officer = args.get("credit_officer", "").strip()
    cbo = args.get("cbo", "").strip()
    loan_type = args.get("loan_type", "").strip()
    status = args.get("status", "").strip()
    from_date = args.get("from_date", "").strip()
    to_date = args.get("to_date", "").strip()
    keyword = args.get("keyword", "").strip()
    loan_id = args.get("loan_id", "").strip()
    search_by = args.get("search_by", "Loan ID").strip()

    if branch and branch.lower() not in ("--all--", "all", ""):
        query["branch"] = branch
    if officer and officer.lower() not in ("--all--", "all", ""):
        query["credit_officer"] = officer
    if cbo and cbo.lower() not in ("--all--", "all", ""):
        query["cbo"] = cbo
    if loan_type and loan_type.lower() not in ("--all--", "all", ""):
        query["loan_type"] = loan_type
    if status and status.lower() not in ("--all--", "all", ""):
        query["status"] = status

    # Date range on reg_date
    date_filter = {}
    if from_date:
        try:
            date_filter["$gte"] = datetime.strptime(from_date, "%Y-%m-%d")
        except ValueError:
            pass
    if to_date:
        try:
            date_filter["$lte"] = datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            pass
    if date_filter:
        query["reg_date"] = date_filter

    # Keyword / loan_id search
    if keyword:
        query["$or"] = [
            {"loan_no": {"$regex": keyword, "$options": "i"}},
            {"client_id": {"$regex": keyword, "$options": "i"}},
        ]
    if loan_id:
        if search_by == "Loan ID":
            query["loan_no"] = {"$regex": loan_id, "$options": "i"}

    guarantor_id = args.get("guarantor_id", "").strip()
    if guarantor_id:
        query["guarantors"] = guarantor_id

    return query


@loan_bp.route("/api/loans", methods=["GET"])
def list_loans():
    db = get_db()
    query = _build_query(request.args)
    loans = [_serialize(l) for l in db.loans.find(query)]
    
    return jsonify({"success": True, "loans": loans}), 200


@loan_bp.route("/api/loans/<loan_id>", methods=["GET"])
def get_loan(loan_id):
    db = get_db()
    doc = None
    try:
        doc = db.loans.find_one({"_id": ObjectId(loan_id)})
    except Exception:
        pass
    if not doc:
        doc = db.loans.find_one({"loan_no": loan_id})
    if not doc:
        return jsonify({"success": False, "message": "Loan not found."}), 404
    return jsonify({"success": True, "loan": _serialize(doc)}), 200


@loan_bp.route("/api/loans", methods=["POST"])
def create_loan():
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    required = ["loan_no", "branch", "client_id", "amount"]
    for field in required:
        if not data.get(field):
            return jsonify({"success": False, "message": f"'{field}' is required."}), 400

    if db.loans.find_one({"loan_no": data["loan_no"]}):
        return jsonify({"success": False, "message": "Loan number already exists."}), 409

    doc = new_loan(
        loan_no=data["loan_no"],
        branch=data["branch"],
        credit_officer=data.get("credit_officer", ""),
        cbo=data.get("cbo", ""),
        client_id=data["client_id"],
        amount=float(data["amount"]),
        loan_type=data.get("loan_type", "Micro Finance"),
        status=data.get("status", "Pending"),
        product=data.get("product"),
        tenor=int(data["tenor"]) if data.get("tenor") is not None else None,
        disbursement_date=data.get("disbursement_date"),
    )
    result = db.loans.insert_one(doc)
    return jsonify({"success": True, "id": str(result.inserted_id)}), 201


@loan_bp.route("/api/loans/<loan_id>/settle", methods=["POST"])
def settle_loan(loan_id):
    db = get_db()
    try:
        oid = ObjectId(loan_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid loan ID."}), 400
        
    loan = db.loans.find_one({"_id": oid})
    if not loan:
        return jsonify({"success": False, "message": "Loan not found."}), 404
        
    db.loans.update_one(
        {"_id": oid},
        {"$set": {"status": "Settled"}}
    )
    
    db.settlements.insert_one({
        "loan_id": loan_id,
        "settled_at": datetime.now(timezone.utc),
        "amount": loan.get("amount", 0.0),
        "user": g.current_user.get("username") if hasattr(g, "current_user") else "system"
    })
    
    return jsonify({"success": True}), 200


@loan_bp.route("/api/loans/<loan_id>", methods=["DELETE"])
def delete_loan(loan_id):
    db = get_db()
    try:
        oid = ObjectId(loan_id)
    except Exception:
        loan_doc = db.loans.find_one({"loan_no": loan_id})
        if loan_doc:
            oid = loan_doc["_id"]
        else:
            return jsonify({"success": False, "message": "Invalid loan ID."}), 400

    # Delete all payments associated with this loan
    db.payments.delete_many({"$or": [{"loan_id": str(oid)}, {"loan_id": oid}]})

    # Delete the loan itself
    result = db.loans.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Loan not found."}), 404

    return jsonify({"success": True, "message": "Loan deleted successfully."}), 200

