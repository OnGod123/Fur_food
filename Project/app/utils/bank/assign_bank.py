import requests

def create_dedicated_account(entity, preferred_bank="wema-bank"):
    """
    entity can be RiderAndStrawler OR Vendor
    Must have paystack_customer_code attribute
    """

    if not entity.paystack_customer_code:
        raise ValueError("Paystack customer not created")

    payload = {
        "customer": entity.paystack_customer_code,
        "preferred_bank": preferred_bank
    }

    res = requests.post(
        f"{PAYSTACK_BASE_URL}/dedicated_account",
        json=payload,
        headers={
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
    )

    data = res.json()

    if not data.get("status"):
        raise Exception(data.get("message", "Failed to create virtual account"))

    account_number = data["data"]["account_number"]

    # Persist only what you need
    entity.paystack_virtual_account = account_number

    return data["data"]

