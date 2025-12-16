import requests
from flask import current_app

MONNIFY_BASE = "https://sandbox.monnify.com/api/v2"

def monnify_payout(
    amount: float,
    reference: str,
    narration: str,
    destination_bank_code: str,
    destination_account_number: str,
    source_account_number: str,
    source_account_name: str,
    source_account_bvn: str,
    async_disbursement: bool = False
):
    """
    Perform a Monnify single disbursement.

    Parameters
    ----------
    amount : float
        Amount in Naira
    reference : str
        Unique reference for this payout
    narration : str
        Description of the transfer
    destination_bank_code : str
        Recipient bank code
    destination_account_number : str
        Recipient account number
    source_account_number : str
        Your source account number
    source_account_name : str
        Your source account name
    source_account_bvn : str
        BVN for source account (required)
    async_disbursement : bool
        If True, perform async disbursement, default is False

    Returns
    -------
    dict
        Monnify API response
    """
    token = current_app.config.get("MONNIFY_SECRET_KEY")  # Bearer token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "amount": amount,
        "reference": reference,
        "narration": narration,
        "destinationBankCode": destination_bank_code,
        "destinationAccountNumber": destination_account_number,
        "currency": "NGN",
        "sourceAccountNumber": source_account_number,
        "senderInfo": {
            "sourceAccountNumber": source_account_number,
            "sourceAccountName": source_account_name,
            "sourceAccountBvn": source_account_bvn,
            "senderBankCode": destination_bank_code
        },
        "async": async_disbursement
    }

    response = requests.post(
        f"{MONNIFY_BASE}/disbursements/single",
        headers=headers,
        json=payload
    )

    if not response.ok:
        raise Exception({"stage": "monnify_payout", "error": response.json()})

    return response.json()
