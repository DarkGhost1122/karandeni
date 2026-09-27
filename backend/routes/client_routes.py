"""
routes/client_routes.py – Client CRUD.

GET  /api/clients           ?branch=&cbo=&keyword=
GET  /api/clients/<id>
POST /api/clients           { nic, first_name, last_name, branch, cbo, contact }
"""
from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime, timezone
from db import get_db
from models.clients import new_client

client_bp = Blueprint("client", __name__)


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if "created_at" in doc and isinstance(doc["created_at"], datetime):
        from datetime import timedelta
        sl_tz = timezone(timedelta(hours=5, minutes=30))
        dt = doc["created_at"]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        doc["created_at"] = dt.astimezone(sl_tz).strftime("%Y-%m-%d")
    
    # Compute full address if not present
    if not doc.get("address"):
        parts = [str(p).strip() for p in [doc.get("house_no"), doc.get("street_address")] if p and str(p).strip()]
        doc["address"] = ", ".join(parts) if parts else (doc.get("street_address") or doc.get("house_no") or "")
    if not doc.get("full_address"):
        doc["full_address"] = doc.get("address")
    return doc


@client_bp.route("/api/clients", methods=["GET"])
def list_clients():
    db = get_db()
    query = {"is_active": True}
    branch = request.args.get("branch", "").strip()
    cbo = request.args.get("cbo", "").strip()
    keyword = request.args.get("keyword", "").strip()
    if branch and branch != "--all--" and branch != "-- All --":
        query["branch"] = branch
    if cbo and cbo != "--all--" and cbo != "-- All --":
        query["cbo"] = cbo
    if keyword:
        query["$or"] = [
            {"full_name": {"$regex": keyword, "$options": "i"}},
            {"nic": {"$regex": keyword, "$options": "i"}},
            {"mobile_no": {"$regex": keyword, "$options": "i"}},
        ]
    clients = [_serialize(c) for c in db.clients.find(query)]
    return jsonify({"success": True, "clients": clients}), 200


@client_bp.route("/api/clients/<client_id>", methods=["GET"])
def get_client(client_id):
    db = get_db()
    doc = None
    try:
        doc = db.clients.find_one({"_id": ObjectId(client_id)})
    except Exception:
        pass
    if not doc:
        doc = db.clients.find_one({"_id": str(client_id)})
    if not doc:
        doc = db.clients.find_one({"nic": str(client_id)})

    if not doc:
        return jsonify({"success": False, "message": "Client not found."}), 404
    return jsonify({"success": True, "client": _serialize(doc)}), 200


@client_bp.route("/api/clients", methods=["POST"])
def create_client():
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    required = ["nic", "first_name", "last_name", "branch"]
    for field in required:
        if not data.get(field):
            return jsonify({"success": False, "message": f"'{field}' is required."}), 400

    # Check NIC uniqueness
    if db.clients.find_one({"nic": data["nic"].upper().strip()}):
        return jsonify({"success": False, "message": "A client with this NIC already exists."}), 409

    doc = new_client(
        nic=data["nic"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        branch=data["branch"],
        cbo=data.get("cbo"),
        contact=data.get("contact"),
        title=data.get("title"),
        initials=data.get("initials"),
        names_denoted_by_initials=data.get("names_denoted_by_initials"),
        gender=data.get("gender"),
        dob=data.get("dob"),
        civil_status=data.get("civil_status"),
        mobile_no=data.get("mobile_no"),
        land_phone=data.get("land_phone"),
        house_no=data.get("house_no"),
        street_address=data.get("street_address"),
        client_level=data.get("client_level", "Level 0"),
        bank_accounts=data.get("bank_accounts"),
        profile_image=data.get("profile_image", ""),
    )
    result = db.clients.insert_one(doc)
    return jsonify({"success": True, "id": str(result.inserted_id)}), 201


@client_bp.route("/api/clients/<client_id>/profile-image", methods=["POST"])
def update_profile_image(client_id):
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    image_data = data.get("image_data", "")
    try:
        oid = ObjectId(client_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid client ID."}), 400
    
    result = db.clients.update_one(
        {"_id": oid},
        {"$set": {"profile_image": image_data}}
    )
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Client not found."}), 404
    return jsonify({"success": True}), 200


@client_bp.route("/api/clients/<client_id>/bank-accounts", methods=["POST"])
def add_bank_account(client_id):
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    bank = data.get("bank", "").strip()
    branch = data.get("branch", "").strip()
    account_number = data.get("account_number", "").strip()
    is_default = bool(data.get("is_default", False))
    
    if not bank or not branch or not account_number:
        return jsonify({"success": False, "message": "Bank, branch, and account number are required."}), 400
        
    try:
        oid = ObjectId(client_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid client ID."}), 400
        
    client = db.clients.find_one({"_id": oid})
    if not client:
        return jsonify({"success": False, "message": "Client not found."}), 404
        
    bank_accounts = client.get("bank_accounts", [])
    
    if is_default:
        for acc in bank_accounts:
            acc["is_default"] = False
            
    new_acc = {
        "bank": bank,
        "branch": branch,
        "account_number": account_number,
        "is_default": is_default
    }
    bank_accounts.append(new_acc)
    
    db.clients.update_one(
        {"_id": oid},
        {"$set": {"bank_accounts": bank_accounts}}
    )
    return jsonify({"success": True, "bank_accounts": bank_accounts}), 200


@client_bp.route("/api/clients/<client_id>/bank-accounts/<int:idx>", methods=["DELETE"])
def delete_bank_account(client_id, idx):
    db = get_db()
    try:
        oid = ObjectId(client_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid client ID."}), 400
        
    client = db.clients.find_one({"_id": oid})
    if not client:
        return jsonify({"success": False, "message": "Client not found."}), 404
        
    bank_accounts = client.get("bank_accounts", [])
    if idx < 0 or idx >= len(bank_accounts):
        return jsonify({"success": False, "message": "Index out of range."}), 400
        
    bank_accounts.pop(idx)
    db.clients.update_one(
        {"_id": oid},
        {"$set": {"bank_accounts": bank_accounts}}
    )
    return jsonify({"success": True, "bank_accounts": bank_accounts}), 200


@client_bp.route("/api/clients/<client_id>/family-members", methods=["POST"])
def add_family_member(client_id):
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    member_name = data.get("member_name", "").strip()
    relationship = data.get("relationship", "").strip()
    member_id = data.get("member_id", "").strip()
    
    if not member_name or not relationship:
        return jsonify({"success": False, "message": "Member name and relationship are required."}), 400
        
    try:
        oid = ObjectId(client_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid client ID."}), 400
        
    client = db.clients.find_one({"_id": oid})
    if not client:
        return jsonify({"success": False, "message": "Client not found."}), 404
        
    family_members = client.get("family_members", [])
    family_members.append({
        "member_name": member_name,
        "relationship": relationship,
        "member_id": member_id
    })
    
    db.clients.update_one(
        {"_id": oid},
        {"$set": {"family_members": family_members}}
    )
    return jsonify({"success": True, "family_members": family_members}), 200


@client_bp.route("/api/clients/<client_id>/family-members/<int:idx>", methods=["DELETE"])
def delete_family_member(client_id, idx):
    db = get_db()
    try:
        oid = ObjectId(client_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid client ID."}), 400
        
    client = db.clients.find_one({"_id": oid})
    if not client:
        return jsonify({"success": False, "message": "Client not found."}), 404
        
    family_members = client.get("family_members", [])
    if idx < 0 or idx >= len(family_members):
        return jsonify({"success": False, "message": "Index out of range."}), 400
        
    family_members.pop(idx)
    db.clients.update_one(
        {"_id": oid},
        {"$set": {"family_members": family_members}}
    )
    return jsonify({"success": True, "family_members": family_members}), 200


@client_bp.route("/api/clients/<client_id>/documents", methods=["POST"])
def add_client_document(client_id):
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    doc_type = data.get("doc_type", "").strip()
    filename = data.get("filename", "").strip()
    file_data = data.get("file_data", "").strip()
    
    if not doc_type or not file_data:
        return jsonify({"success": False, "message": "doc_type and file_data are required."}), 400
        
    try:
        oid = ObjectId(client_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid client ID."}), 400
        
    client = db.clients.find_one({"_id": oid})
    if not client:
        return jsonify({"success": False, "message": "Client not found."}), 404
        
    from datetime import timedelta
    sl_tz = timezone(timedelta(hours=5, minutes=30))
    submitted_at = datetime.now(sl_tz).strftime("%Y-%m-%d %I:%M %p")
    
    new_doc = {
        "doc_type": doc_type,
        "filename": filename or f"{doc_type.lower().replace(' ', '_')}.jpg",
        "file_data": file_data,
        "submitted_at": submitted_at
    }
    
    db.clients.update_one(
        {"_id": oid},
        {"$push": {"documents": new_doc}}
    )
    
    updated_client = db.clients.find_one({"_id": oid})
    docs = updated_client.get("documents", [])
    return jsonify({"success": True, "documents": docs}), 200


@client_bp.route("/api/clients/<client_id>/documents/<int:idx>", methods=["DELETE"])
def delete_client_document(client_id, idx):
    db = get_db()
    try:
        oid = ObjectId(client_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid client ID."}), 400
        
    client = db.clients.find_one({"_id": oid})
    if not client:
        return jsonify({"success": False, "message": "Client not found."}), 404
        
    documents = client.get("documents", [])
    if idx < 0 or idx >= len(documents):
        return jsonify({"success": False, "message": "Index out of range."}), 400
        
    documents.pop(idx)
    db.clients.update_one(
        {"_id": oid},
        {"$set": {"documents": documents}}
    )
    return jsonify({"success": True, "documents": documents}), 200


@client_bp.route("/api/admin/clear-database", methods=["POST", "GET"])
def clear_database():
    db = get_db()
    # Drop/delete transactional collections
    db.clients.delete_many({})
    db.loans.delete_many({})
    db.payments.delete_many({})
    db.cbos.delete_many({})
    db.cbo_members.delete_many({})
    db.cbo_attendance.delete_many({})
    db.meetings.delete_many({})
    db.savings_accounts.delete_many({})
    db.savings_transactions.delete_many({})
    db.group_members.delete_many({})
    db.settlements.delete_many({})
    db.cash_movements.delete_many({})
    
    # Reset branches to only KARANDENIYA (is_active: True)
    db.branches.delete_many({})
    db.branches.insert_one({
        "name": "KARANDENIYA",
        "code": "KDN",
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    })
        
    return jsonify({"success": True, "message": "Database cleared successfully (initialized fresh with KARANDENIYA branch)."}), 200


@client_bp.route("/api/admin/seed-test-data", methods=["POST", "GET"])
def seed_test_data():
    db = get_db()
    
    # 1. Clear transactional data
    db.clients.delete_many({})
    db.loans.delete_many({})
    db.payments.delete_many({})
    db.cbo_members.delete_many({})
    db.cbo_attendance.delete_many({})
    db.meetings.delete_many({})
    db.savings_accounts.delete_many({})
    db.savings_transactions.delete_many({})
    db.group_members.delete_many({})
    db.settlements.delete_many({})
    db.cash_movements.delete_many({})
    
    # 2. Check/Ensure Branch exists
    branch_name = "ANAMADUWA"
    if not db.branches.find_one({"name": branch_name}):
        db.branches.insert_one({
            "name": branch_name,
            "code": "AND",
            "created_at": datetime.now(timezone.utc)
        })
        
    # 3. Check/Ensure CBO exists
    cbo_name = "001 -- BURUTHAKALE-01"
    if not db.cbos.find_one({"name": cbo_name}):
        db.cbos.insert_one({
            "name": cbo_name,
            "branch_id": branch_name,
            "credit_officer": "officer1",
            "cbo_code": "001",
            "meeting_day": "Tuesday",
            "meeting_time": "11:00",
            "cbo_leader": "No Leader",
            "created_at": datetime.now(timezone.utc)
        })

    # 4. Create Client
    from models.clients import new_client
    client_doc = new_client(
        nic="200511903909",
        first_name="Y",
        last_name="LAKSHAN",
        branch=branch_name,
        cbo=cbo_name,
        contact="0771234567",
        title="Mr",
        initials="Y",
        names_denoted_by_initials="YASINDU",
        gender="Male",
        dob="",
        civil_status="Single",
        mobile_no="0771234567",
        land_phone="",
        house_no="",
        street_address="",
        client_level="Level 0",
        bank_accounts=[],
        profile_image=""
    )
    client_doc["cbo_position"] = "President"
    client_doc["cbo_eligibility"] = "Eligible"
    client_doc["group_code"] = "001 - G-1"
    client_doc["has_group"] = True
    
    db.clients.insert_one(client_doc)
    client_id = str(client_doc["_id"])
    
    # 5. Create CBO Member record
    db.cbo_members.insert_one({
        "cbo": cbo_name,
        "client_nic": "200511903909",
        "position": "President",
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    })
    
    # 6. Create Loan (Disbursed status)
    from models.loans import new_loan
    from datetime import timedelta
    loan_doc = new_loan(
        loan_no="LN1000",
        branch=branch_name,
        credit_officer="officer1",
        cbo=cbo_name,
        client_id=client_id,
        amount=40000.0,
        loan_type="Micro Finance",
        status="Disbursed",
        product="Micro Finance",
        tenor=24,
        disbursement_date=datetime.now(timezone.utc) - timedelta(days=1)
    )
    loan_doc["reg_date"] = datetime.now(timezone.utc) - timedelta(days=1)
    loan_doc["paid_amount"] = 0.0
    
    db.loans.insert_one(loan_doc)
    loan_id = str(loan_doc["_id"])
    
    # 7. Record Payment
    pay_doc = {
        "loan_id": loan_id,
        "amount": 2000.0,
        "payment_date": datetime.now(timezone.utc),
        "collected_by": "asindu"
    }
    db.payments.insert_one(pay_doc)
    
    # Increment paid amount in loan
    db.loans.update_one(
        {"_id": ObjectId(loan_id)},
        {"$inc": {"paid_amount": 2000.0}}
    )
    
    return jsonify({"success": True, "message": "E2E verification data seeded successfully."}), 200


@client_bp.route("/api/admin/debug-db", methods=["GET"])
def debug_db():
    db = get_db()
    branches = list(db.branches.find({}, {"_id": 0}))
    cbos = list(db.cbos.find({}, {"_id": 0}))
    users = list(db.users.find({}, {"_id": 0, "username": 1, "role": 1}))
    clients = list(db.clients.find({}, {"full_name": 1, "nic": 1, "branch": 1, "cbo": 1, "is_active": 1}))
    for c in clients:
        c["id"] = str(c.pop("_id"))
    loans = list(db.loans.find({}, {"loan_no": 1, "client_id": 1, "branch": 1, "cbo": 1, "status": 1}))
    for l in loans:
        l["id"] = str(l.pop("_id"))
    payments = list(db.payments.find({}))
    for p in payments:
        p["id"] = str(p.pop("_id"))
        if "payment_date" in p and isinstance(p["payment_date"], datetime):
            p["payment_date"] = p["payment_date"].strftime("%Y-%m-%d %I:%M %p")
        if "date" in p and isinstance(p["date"], datetime):
            p["date"] = p["date"].strftime("%Y-%m-%d %I:%M %p")
    return jsonify({
        "branches": branches,
        "cbos": cbos,
        "users": users,
        "clients": clients,
        "loans": loans,
        "payments": payments
    }), 200


@client_bp.route("/api/admin/run-seeder", methods=["POST", "GET"])
def run_seeder_endpoint():
    try:
        from seed import seed as run_seeding
        run_seeding()
        return jsonify({"success": True, "message": "Seeder executed successfully."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


