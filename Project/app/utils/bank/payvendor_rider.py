import requests
from flask import current_app
from app.Database.vendors_model import Vendor
from app.Database.RiderAndStrawler import RiderAndStrawler
from app.extensions import session_scope


def pay_vendor_or_rider(
    *,
    target_type: str,   # "vendor" | "rider"
    target_id: int,
    amount: int,        # NAIRA
    narration: str
) -> dict:
    """
    Unified payout function for vendors and riders.

    - Reads bank details from DB
    - Uses Paystack transfer API
    - Uses session_scope
    """

    if target_type not in ("vendor", "rider"):
        raise ValueError("target_type must be 'vendor' or 'rider'")

    if amount <= 0:
        raise ValueError("Amount must be positive")

    with session_scope() as session:
        if target_type == "vendor":
            target = (
                session.query(Vendor)
                .filter_by(id=target_id, is_verified=True)
                .first()
            )
        else:
            target = (
                session.query(RiderAndStrawler)
                .filter_by(id=target_id, is_verified=True)
                .first()
            )

        if not target:
            raise ValueError(f"{target_type.capitalize()} not found or not verified")

        account_number = target.account_number
        bank_code = target.bank_code
        account_name = target.account_name

    # Convert to kobo (Paystack requirement)
    amount_kobo = amount * 100

    headers = {
        "Authorization": f"Bearer {current_app.config['PAYSTACK_SECRET_KEY']}",
        "Content-Type": "application/json",
    }

    payload = {
        "source": "balance",
        "amount": amount_kobo,
        "reason": narration,
        "recipient": {
            "type": "nuban",
            "name": account_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN",
        },
    }

    response = requests.post(
        current_app.config["PAYSTACK_TRANSFER_URL"],
        json=payload,
        headers=headers,
        timeout=20,
    )

    data = response.json()

    if not data.get("status"):
        raise RuntimeError(f"Paystack error: {data.get('message')}")

    return data

