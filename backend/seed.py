"""
seed.py – Seeds initial configuration for Karandeni Investment.

Creates:
  - Default Admin user (username: asindu, password: 1234)
  - Default Branch: KARANDENIYA (Code: KDN)
  - Prepares empty collections and database indexes

Usage:
  python seed.py          # Seeds initial admin and default branch safely
  python seed.py --reset  # Wipes existing collections and re-seeds clean state
"""
import sys
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Add backend dir to path so imports work
sys.path.insert(0, os.path.dirname(__file__))

from db import get_db
from auth import hash_password
from models.users import new_user


def seed(reset: bool = False):
    db = get_db()
    print("═══════════════════════════════════════════════════════════════")
    print("  Karandeni Investment – Database Initializer & Seeder")
    print("═══════════════════════════════════════════════════════════════")

    if reset:
        print("\n▶ [RESET] Clearing all transactional collections...")
        collections_to_clear = [
            "clients", "loans", "payments", "cbos", "cbo_members",
            "cbo_attendance", "meetings", "savings_accounts",
            "savings_transactions", "group_members", "settlements",
            "cash_movements"
        ]
        for col in collections_to_clear:
            count = db[col].count_documents({})
            if count > 0:
                db[col].delete_many({})
                print(f"  - Cleared {count} records from '{col}'")
        print("  ✓ Transactional database reset complete.")

    # ── 1. Create Database Indexes ──────────────────────────────────────────
    print("\n▶ Ensuring database indexes...")
    try:
        from db import _ensure_indexes
        _ensure_indexes(db)
        print("  ✓ Indexes verified.")
    except Exception as e:
        print(f"  [WARN] Index creation: {e}")

    # ── 2. Admin User ────────────────────────────────────────────────────────
    admin_username = os.getenv("ADMIN_USERNAME", "asindu")
    admin_password = os.getenv("ADMIN_PASSWORD", "1234")
    admin_display = os.getenv("ADMIN_DISPLAY_NAME", "ASINDU YASITH")

    existing_admin = db.users.find_one({"username": admin_username})
    if existing_admin:
        print(f"  [SKIP] Admin user '{admin_username}' already exists.")
    else:
        hashed = hash_password(admin_password)
        doc = new_user(
            username=admin_username,
            password_hash=hashed,
            display_name=admin_display,
            role="admin",
        )
        doc["branch"] = "KARANDENIYA"
        db.users.insert_one(doc)
        print(f"  [OK]   Created admin user '{admin_username}' (password: {admin_password})")

    # ── 3. Default Branch ───────────────────────────────────────────────────
    default_branch = "KARANDENIYA"
    default_code = "KDN"
    existing_branch = db.branches.find_one({"name": default_branch})
    if existing_branch:
        print(f"  [SKIP] Branch '{default_branch}' already exists.")
    else:
        db.branches.insert_one({
            "name": default_branch,
            "code": default_code,
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        })
        print(f"  [OK]   Created default branch '{default_branch}' ({default_code})")

    print("\n═══════════════════════════════════════════════════════════════")
    print(f"  Initialization Complete for Karandeni Investment!")
    print(f"  Login Username: {admin_username}")
    print(f"  Login Password: {admin_password}")
    print("  Database is clean and ready for real customer operations.")
    print("═══════════════════════════════════════════════════════════════\n")


if __name__ == "__main__":
    should_reset = "--reset" in sys.argv
    seed(reset=should_reset)
