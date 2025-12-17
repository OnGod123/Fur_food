import requests
from flask import current_app

PAYSTACK_BASE = "https://api.paystack.co"


def paystack_charge_bank(email: str, amount: float, bank_code: str, account_number: str,
                    disable_otp: bool = False, otp: str = None) -> dict:
    """
    Perform a full Paystack payout to a Nigerian bank account, including transfer finalization.

    Parameters
    ----------
    email : str
        Recipient's email (used as name for recipient)
    amount : float
        Amount in Naira
    bank_code : str
        Paystack bank code
    account_number : str
        Nigerian 10-digit bank account number
    disable_otp : bool
        If True, disables OTP (only needed once)
    otp : str
        OTP sent to your phone/email to finalize OTP disable and transfer

    Returns
    -------
    dict
        Final transfer response from Paystack
    """
    headers = {
        "Authorization": f"Bearer {current_app.config['PAYSTACK_SECRET_KEY']}",
        "Content-Type": "application/json",
    }

    # Step 0: Optionally disable OTP
    if disable_otp:
        disable_res = requests.post(f"{PAYSTACK_BASE}/transfer/disable_otp", headers=headers)
        if not disable_res.ok:
            raise Exception({"stage": "disable_otp", "error": disable_res.json()})

        if otp is None:
            raise ValueError("OTP is required to finalize disabling OTP")

        finalize_res = requests.post(
            f"{PAYSTACK_BASE}/transfer/disable_otp_finalize",
            headers=headers,
            json={"otp": otp}
        )
        if not finalize_res.ok:
            raise Exception({"stage": "finalize_disable_otp", "error": finalize_res.json()})

    # Step 1: Create recipient
    recipient_payload = {
        "type": "nuban",
        "name": email,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": "NGN"
    }

    recipient_res = requests.post(
        f"{PAYSTACK_BASE}/transferrecipient",
        json=recipient_payload,
        headers=headers
    )
    if not recipient_res.ok:
        raise Exception({"stage": "recipient", "error": recipient_res.json()})

    recipient_code = recipient_res.json()["data"]["recipient_code"]

    # Step 2: Initiate transfer
    transfer_payload = {
        "source": "balance",
        "amount": int(amount * 100),  # convert Naira to Kobo
        "recipient": recipient_code,
        "reason": f"Vendor Payout to {email}",
    }

    transfer_res = requests.post(
        f"{PAYSTACK_BASE}/transfer",
        json=transfer_payload,
        headers=headers
    )
    if not transfer_res.ok:
        raise Exception({"stage": "transfer", "error": transfer_res.json()})

    transfer_code = transfer_res.json()["data"]["transfer_code"]

    # Step 3: Finalize transfer
    if otp is None:
        raise ValueError("OTP is required to finalize the transfer")

    finalize_payload = {
        "transfer_code": transfer_code,
        "otp": otp
    }

    finalize_res = requests.post(
        f"{PAYSTACK_BASE}/transfer/finalize_transfer",
        headers=headers,
        json=finalize_payload
    )
    if not finalize_res.ok:
        raise Exception({"stage": "finalize_transfer", "error": finalize_res.json()})

    return finalize_res.json()
