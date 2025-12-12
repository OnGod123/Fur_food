import random
from app.extensions import r

def verify_otp_code(phone: str, otp: str, context="login") -> dict:
    key = f"otp:{context}:{phone}"
    stored_otp = r.get(key)

    # ------------------------------------------------------
    # OTP MISSING OR EXPIRED
    # ------------------------------------------------------
    if not stored_otp:
        return {"valid": False, "reason": "OTP expired or not found"}

    # Convert Redis bytes → string
    stored_otp = stored_otp.decode()

    # ------------------------------------------------------
    # WRONG OTP
    # ------------------------------------------------------
    if stored_otp != otp:
        return {"valid": False, "reason": "Incorrect OTP"}

    # OTP is correct — remove it so it can't be reused
    r.delete(key)

    # ------------------------------------------------------
    # CHECK IF PHONE HAS BEEN VERIFIED BEFORE
    # ------------------------------------------------------
    verified_key = f"verified_phone:{phone}"

    if r.exists(verified_key):
        return {
            "valid": True,
            "already_verified": True,
            "message": "Phone already verified before"
        }

    # ------------------------------------------------------
    # FIRST TIME VERIFICATION → MARK AS VERIFIED
    # ------------------------------------------------------
    r.set(verified_key, "true")  # No TTL → permanent verification

    return {
        "valid": True,
        "already_verified": False,
        "message": "Phone verified successfully"
    }import random
from app.extensions import r

def verify_otp_code(phone: str, otp: str, context="login") -> dict:
    key = f"otp:{context}:{phone}"
    stored_otp = r.get(key)

    # ------------------------------------------------------
    # OTP MISSING OR EXPIRED
    # ------------------------------------------------------
    if not stored_otp:
        return {"valid": False, "reason": "OTP expired or not found"}

    # Convert Redis bytes → string
    stored_otp = stored_otp.decode()

    # ------------------------------------------------------
    # WRONG OTP
    # ------------------------------------------------------
    if stored_otp != otp:
        return {"valid": False, "reason": "Incorrect OTP"}

    # OTP is correct — remove it so it can't be reused
    r.delete(key)

    # ------------------------------------------------------
    # CHECK IF PHONE HAS BEEN VERIFIED BEFORE
    # ------------------------------------------------------
    verified_key = f"verified_phone:{phone}"

    if r.exists(verified_key):
        return {
            "valid": True,
            "already_verified": True,
            "message": "Phone already verified before"
        }

    # ------------------------------------------------------
    # FIRST TIME VERIFICATION → MARK AS VERIFIED
    # ------------------------------------------------------
    r.set(verified_key, "true")  # No TTL → permanent verification

    return {
        "valid": True,
        "already_verified": False,
        "message": "Phone verified successfully"
    }
