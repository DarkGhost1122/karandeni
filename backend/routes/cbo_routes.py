"""
routes/cbo_routes.py – Branches, CBOs, Credit Officers (lookup data).

GET /api/branches
GET /api/cbos?branch=<name>
GET /api/credit-officers?branch=<name>
"""
from flask import Blueprint, request, jsonify
from db import get_db

cbo_bp = Blueprint("cbo", __name__)


@cbo_bp.route("/api/branches", methods=["GET"])
def get_branches():
    db = get_db()
    branches = list(db.branches.find({"is_active": True}, {"_id": 0, "name": 1, "code": 1}))
    return jsonify({"success": True, "branches": branches}), 200


@cbo_bp.route("/api/cbos", methods=["GET"])
def get_cbos():
    db = get_db()
    branch = request.args.get("branch", "").strip()
    query = {"is_active": True}
    if branch and branch != "--all--":
        query["branch_id"] = branch
    cbos = list(db.cbos.find(query, {"_id": 0, "name": 1, "branch_id": 1, "credit_officer": 1}))
    return jsonify({"success": True, "cbos": cbos}), 200


@cbo_bp.route("/api/credit-officers", methods=["GET"])
def get_credit_officers():
    """Return distinct credit officers, optionally filtered by branch."""
    db = get_db()
    branch = request.args.get("branch", "").strip()
    query = {"is_active": True}
    if branch and branch != "--all--":
        query["branch"] = branch
    officers = list(db.users.find(
        {**query, "role": "credit_officer"},
        {"_id": 0, "username": 1, "display_name": 1}
    ))
    return jsonify({"success": True, "officers": officers}), 200


@cbo_bp.route("/api/cbos", methods=["POST"])
def create_cbo():
    from models.cbos import new_cbo
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    
    required = ["name", "branch_id"]
    for field in required:
        if not data.get(field):
            return jsonify({"success": False, "message": f"'{field}' is required."}), 400

    name_strip = data["name"].strip()
    if db.cbos.find_one({"name": name_strip}):
        return jsonify({"success": False, "message": f"CBO '{name_strip}' already exists."}), 409

    doc = new_cbo(
        name=data["name"],
        branch_id=data["branch_id"],
        credit_officer=data.get("credit_officer"),
        cbo_code=data.get("cbo_code", "001"),
        meeting_day=data.get("meeting_day", "Tuesday"),
        meeting_time=data.get("meeting_time", "11:00"),
        cbo_leader=data.get("cbo_leader", "No Leader"),
    )
    result = db.cbos.insert_one(doc)
    return jsonify({"success": True, "id": str(result.inserted_id)}), 201
