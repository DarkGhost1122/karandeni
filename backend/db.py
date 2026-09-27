"""
db.py – MongoDB connection and collection access.
"""
import os
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv()

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "karandeni_investment")
        _client = MongoClient(uri)
        _db = _client[db_name]
        _ensure_indexes(_db)
    return _db


def _ensure_indexes(db):
    """Create indexes that enforce uniqueness and speed up common queries."""
    # Users – username must be unique
    db.users.create_index([("username", ASCENDING)], unique=True)

    # Loans
    db.loans.create_index([("loan_no", ASCENDING)], unique=True, sparse=True)
    db.loans.create_index([("branch", ASCENDING), ("status", ASCENDING)])
    db.loans.create_index([("client_id", ASCENDING)])

    # Clients
    db.clients.create_index([("nic", ASCENDING)], unique=True, sparse=True)
    db.clients.create_index([("branch", ASCENDING)])

    # CBOs
    db.cbos.create_index([("branch_id", ASCENDING)])

    # Payments
    db.payments.create_index([("loan_id", ASCENDING)])

    # Settlements
    db.settlements.create_index([("loan_id", ASCENDING)])
