import uuid
import requests
from flask import current_app

def flutterwave_payout(amount, bank_code, account_number, email, narration="Vendor Payout"):
    """
    Pay a vendor using Flutterwave v3 Transfer API.

    Returns simplified:
        { id, status, amount, fee, bank_name, reference }
    """

    url = "https://api.flutterwave.com/v3/transfers"

    reference = f"vendor-payout-{uuid.uuid4().hex[:10]}"

    payload = {
        "account_bank": bank_code,          # e.g. "044"
        "account_number": account_number,   # vendor's account number
        "amount": amount,
        "currency": "NGN",
        "debit_currency": "NGN",
        "narration": narration,
        "reference": reference,
        "meta": {
            "vendor_email": email
        }
    }

    headers = {
        "Authorization": f"Bearer {current_app.config['FLW_SECRET_KEY']}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

    except Exception as e:
        raise Exception(f"Flutterwave request failed: {str(e)}")

    if data.get("status") != "success":
        raise Exception(f"Flutterwave transfer failed: {data.get('message')}")

    tr = data["data"]

    return {
        "id": tr["id"],
        "status": tr["status"],       # NEW / PENDING / SUCCESSFUL
        "amount": tr["amount"],
        "fee": tr.get("fee", 0),
        "bank_name": tr.get("bank_name"),
        "reference": tr.get("reference")
    }
