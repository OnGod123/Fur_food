
import requests
from flask import current_app

def resolve_bank_account(account_number: str, bank_code: str) -> dict | None:
    url = "https://api.paystack.co/bank/resolve"
    headers = {
        "Authorization": f"Bearer {current_app.config['PAYSTACK_SECRET_KEY']}"
    }
    params = {
        "account_number": account_number,
        "bank_code": bank_code
    }

    resp = requests.get(url, headers=headers, params=params, timeout=10)
    if resp.status_code != 200:
        return None

    data = resp.json()
    if not data.get("status"):
        return None

    return data["data"]  # account_name, account_number

