"""models/clients.py – Client document helpers."""
from datetime import datetime, timezone


def new_client(
    nic: str,
    first_name: str,
    last_name: str,
    branch: str,
    cbo: str = None,
    contact: str = None,
    title: str = None,
    initials: str = None,
    names_denoted_by_initials: str = None,
    gender: str = None,
    dob: str = None,
    civil_status: str = None,
    mobile_no: str = None,
    land_phone: str = None,
    house_no: str = None,
    street_address: str = None,
    client_level: str = "Level 0",
    bank_accounts: list = None,
    profile_image: str = "",
) -> dict:
    parts = [p.strip() for p in [house_no, street_address] if p and p.strip()]
    full_addr = ", ".join(parts) if parts else (street_address or house_no or "")
    return {
        "nic": nic.upper().strip(),
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "full_name": f"{first_name.strip()} {last_name.strip()}",
        "branch": branch,
        "cbo": cbo,
        "contact": contact or mobile_no,
        "title": title,
        "initials": initials,
        "names_denoted_by_initials": names_denoted_by_initials,
        "gender": gender,
        "dob": dob,
        "civil_status": civil_status,
        "mobile_no": mobile_no or contact,
        "land_phone": land_phone,
        "house_no": house_no,
        "street_address": street_address,
        "address": full_addr,
        "full_address": full_addr,
        "client_level": client_level,
        "bank_accounts": bank_accounts if bank_accounts is not None else [],
        "profile_image": profile_image,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

