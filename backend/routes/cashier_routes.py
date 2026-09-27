"""
routes/cashier_routes.py – Loan Disbursement, Group Payments, Collection.

GET  /api/disburse-loans                   ?branch=&credit_officer=&cbo=
POST /api/disburse-loans/<id>/disburse
POST /api/disburse-loans/<id>/send-back
GET  /api/group-payments                   ?branch=&date=&cbo=&loan_type=
GET  /api/collection                       ?branch=&date=&loan_type=
"""
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from datetime import datetime, timezone
from db import get_db
from services.sms_service import trigger_loan_repayment_sms

cashier_bp = Blueprint("cashier", __name__)


def _serialize_loan(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    from datetime import timedelta
    sl_tz = timezone(timedelta(hours=5, minutes=30))
    for f in ["reg_date", "disbursement_date", "created_at"]:
        if doc.get(f) and isinstance(doc[f], datetime):
            dt = doc[f]
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            doc[f] = dt.astimezone(sl_tz).strftime("%Y-%m-%d")
    return doc


# ── Loan Disbursement ─────────────────────────────────────────────────────

@cashier_bp.route("/api/disburse-loans", methods=["GET"])
def disburse_list():
    db = get_db()
    
    # Resolve client queries to support client's assigned CBO robustly
    client_query = {}
    branch = request.args.get("branch", "").strip()
    cbo = request.args.get("cbo", "").strip()
    if branch and branch.lower() not in ("--all--", "all", ""):
        client_query["branch"] = branch
    if cbo and cbo.lower() not in ("--all--", "all", ""):
        client_query["cbo"] = cbo

    client_ids = []
    if client_query:
        client_docs = list(db.clients.find(client_query))
        for c in client_docs:
            client_ids.append(str(c["_id"]))
            if c.get("nic"):
                client_ids.append(c["nic"])
        if not client_ids:
            return jsonify({"success": True, "loans": []}), 200

    query = {"status": {"$in": ["Pending", "Approved"]}}
    if client_ids:
        query["client_id"] = {"$in": client_ids}
    elif branch and branch.lower() not in ("--all--", "all", ""):
        # Fallback filter directly on loan if no CBO was selected
        query["branch"] = branch

    officer = request.args.get("credit_officer", "").strip()
    if officer and officer.lower() not in ("--all--", "all", ""):
        query["credit_officer"] = officer

    loans = [_serialize_loan(l) for l in db.loans.find(query)]
    
    for l in loans:
        client_doc = None
        try:
            client_doc = db.clients.find_one({"_id": ObjectId(l["client_id"])})
        except Exception:
            pass
        if not client_doc:
            client_doc = db.clients.find_one({"nic": l["client_id"]})
        if client_doc:
            l["client_name"] = client_doc.get("full_name") or f"{client_doc.get('first_name','')} {client_doc.get('last_name','')}"
            l["cbo"] = client_doc.get("cbo", "")
            
    return jsonify({"success": True, "loans": loans}), 200


@cashier_bp.route("/api/disburse-loans/<loan_id>/disburse", methods=["POST"])
def disburse_loan(loan_id):
    db = get_db()
    try:
        oid = ObjectId(loan_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid loan ID."}), 400

    result = db.loans.update_one(
        {"_id": oid, "status": {"$in": ["Pending", "Approved"]}},
        {"$set": {"status": "Disbursed", "disbursement_date": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Loan not found or not in Pending or Approved status."}), 404
    return jsonify({"success": True}), 200


@cashier_bp.route("/api/disburse-loans/<loan_id>/send-back", methods=["POST"])
def send_back_loan(loan_id):
    db = get_db()
    try:
        oid = ObjectId(loan_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid loan ID."}), 400

    result = db.loans.update_one(
        {"_id": oid, "status": {"$in": ["Pending", "Approved"]}},
        {"$set": {"status": "Sent Back"}}
    )
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Loan not found or not in Pending or Approved status."}), 404
    return jsonify({"success": True}), 200


# ── Group Payments ────────────────────────────────────────────────────────

@cashier_bp.route("/api/group-payments", methods=["GET"])
def group_payments():
    db = get_db()
    branch = request.args.get("branch", "").strip()
    cbo = request.args.get("cbo", "").strip()
    loan_type = request.args.get("loan_type", "").strip()
    date_str = request.args.get("date", "").strip()

    from datetime import timedelta

    payments_list = []
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            pq = {"payment_date": {"$gte": dt, "$lt": dt + timedelta(days=1)}}
            db_payments = list(db.payments.find(pq))
            
            for p in db_payments:
                # Fetch loan details
                loan = None
                if p.get("loan_id"):
                    loan = db.loans.find_one({"_id": ObjectId(p["loan_id"])})
                
                if not loan:
                    continue
                
                # Check branch, CBO and loan_type filters
                if branch and branch.lower() not in ("--all--", "all", ""):
                    if loan.get("branch") != branch:
                        continue
                if cbo and cbo.lower() not in ("--all--", "all", ""):
                    if loan.get("cbo") != cbo:
                        continue
                if loan_type and loan_type.lower() not in ("--all--", "all", ""):
                    if loan.get("loan_type") != loan_type:
                        continue
                
                pay_dt = p.get("payment_date")
                if isinstance(pay_dt, datetime):
                    from datetime import timedelta
                    sl_tz = timezone(timedelta(hours=5, minutes=30))
                    if pay_dt.tzinfo is None:
                        pay_dt = pay_dt.replace(tzinfo=timezone.utc)
                    pay_dt_str = pay_dt.astimezone(sl_tz).strftime("%Y-%m-%d")
                else:
                    pay_dt_str = ""
                
                payments_list.append({
                    "id": str(p["_id"]),
                    "loan_id": str(p["loan_id"]),
                    "loan_no": loan.get("loan_no", ""),
                    "client_name": loan.get("client_name", ""),
                    "cbo": loan.get("cbo", ""),
                    "amount": p.get("amount", 0.0),
                    "payment_date": pay_dt_str,
                    "collected_by": p.get("collected_by", "")
                })
        except Exception as e:
            print("Error in group_payments API:", e)
            pass

    return jsonify({"success": True, "payments": payments_list}), 200


# ── Collection ─────────────────────────────────────────────────────────────

@cashier_bp.route("/api/collection", methods=["GET"])
def collection():
    db = get_db()
    query = {}
    branch = request.args.get("branch", "").strip()
    loan_type = request.args.get("loan_type", "").strip()
    if branch and branch.lower() not in ("--all--", "all", ""):
        query["branch"] = branch
    if loan_type and loan_type.lower() not in ("--all--", "all", ""):
        query["loan_type"] = loan_type

    loans = [_serialize_loan(l) for l in db.loans.find({**query, "status": "Active"})]
    return jsonify({"success": True, "loans": loans}), 200


@cashier_bp.route("/api/group-payments/sheet", methods=["GET"])
def group_payments_sheet():
    db = get_db()
    branch = request.args.get("branch", "").strip()
    cbo = request.args.get("cbo", "").strip()
    loan_type = request.args.get("loan_type", "").strip()
    
    # Match client CBO dynamically rather than hardcoded loan CBO
    client_query = {"is_active": True}
    if branch and branch.lower() not in ("--all--", "all", ""):
        client_query["branch"] = branch
    if cbo and cbo.lower() not in ("--all--", "all", ""):
        client_query["cbo"] = cbo
        
    client_docs = list(db.clients.find(client_query))
    client_map = {}
    client_ids = []
    for c in client_docs:
        client_map[str(c["_id"])] = c
        if c.get("nic"):
            client_map[c["nic"]] = c
        client_ids.append(str(c["_id"]))
        if c.get("nic"):
            client_ids.append(c["nic"])
            
    if not client_ids:
        return jsonify({"success": True, "loans": []}), 200
        
    query = {
        "status": {"$in": ["Pending", "Approved", "Disbursed", "Active"]},
        "client_id": {"$in": client_ids}
    }
    if loan_type and loan_type.lower() not in ("--all--", "all", ""):
        query["loan_type"] = loan_type

    loans = list(db.loans.find(query))
    sheet_data = []

    for l in loans:
        client = client_map.get(l.get("client_id"))
        if not client:
            continue
            
        group_code = client.get("group_code") or ""
        group_label = group_code.split(" - ").pop() if " - " in group_code else group_code
        if not group_label:
            group_label = "Unassigned"
            
        created_at_dt = client.get("created_at") or datetime.now()
        c_code = int(created_at_dt.timestamp() * 1000)
        
        amount = float(l.get("amount", 0.0))
        weeks = int(l.get("tenor") or 24)
        payback = amount + (amount * 0.0155 * weeks)
        if amount == 10000 and weeks == 13:
            payback = 12600.0
        elif amount == 15000 and weeks == 13:
            payback = 19000.0
        payment = round(payback / weeks) if weeks > 0 else 0

        # Query actual payments
        loan_id = l.get("_id")
        payments = list(db.payments.find({"$or": [{"loan_id": str(loan_id)}, {"loan_id": loan_id}]}))
        paid_amount = sum(float(p.get("amount", 0.0)) for p in payments)
        
        # Balance is full agreed amount (principal + interest) minus total paid
        balance = max(0.0, payback - paid_amount)
        
        sheet_data.append({
            "loan_id": str(l["_id"]),
            "loan_no": l.get("loan_no", ""),
            "nic": client.get("nic", ""),
            "client_name": client.get("full_name") or f"{client.get('first_name','')} {client.get('last_name','')}",
            "c_code": str(c_code),
            "group_label": group_label,
            "balance": balance,
            "payment": payment,
            "payback": payback,
            "paid_amount": paid_amount
        })
        
    return jsonify({"success": True, "loans": sheet_data}), 200


@cashier_bp.route("/api/group-payments/submit", methods=["POST"])
def group_payments_submit():
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    payments = data.get("payments", [])
    collected_by = g.current_user.get("username") if hasattr(g, "current_user") and g.current_user else "admin"

    if not payments:
        return jsonify({"success": False, "message": "No payments provided."}), 400

    inserted_count = 0
    for p in payments:
        loan_id_str = p.get("loan_id")
        amount = float(p.get("amount", 0.0))
        if amount <= 0:
            continue
            
        pay_doc = {
            "loan_id": loan_id_str,
            "amount": amount,
            "payment_date": datetime.now(timezone.utc),
            "collected_by": collected_by
        }
        db.payments.insert_one(pay_doc)
        
        db.loans.update_one(
            {"_id": ObjectId(loan_id_str)},
            {"$inc": {"paid_amount": amount}}
        )
        inserted_count += 1
        
        # Dispatch automated repayment SMS via SMSlenz
        try:
            trigger_loan_repayment_sms(db, loan_id_str, amount)
        except Exception as sms_err:
            print(f"[Cashier] SMS trigger error for loan {loan_id_str}: {sms_err}")
        
    return jsonify({"success": True, "message": f"Successfully recorded {inserted_count} payments."}), 200


@cashier_bp.route("/api/payments/<payment_id>", methods=["DELETE"])
def delete_payment(payment_id):
    db = get_db()
    try:
        pid = ObjectId(payment_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid payment ID."}), 400

    payment = db.payments.find_one({"_id": pid})
    if not payment:
        return jsonify({"success": False, "message": "Payment not found."}), 404

    # Decrement loan's paid_amount
    loan_id_str = payment.get("loan_id")
    amount = float(payment.get("amount", 0.0))
    if loan_id_str:
        db.loans.update_one(
            {"_id": ObjectId(loan_id_str)},
            {"$inc": {"paid_amount": -amount}}
        )

    # Delete the payment record
    db.payments.delete_one({"_id": pid})

    return jsonify({"success": True, "message": "Payment reversed successfully."}), 200
