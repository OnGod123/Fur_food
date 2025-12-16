import uuid
from datetime import datetime
from flask import current_app
from app.extensions import db
from app.merchants.Database.vendors_data_base import Vendor
from app.merchants.Database.Vendors_payment_service import Vendor_Payment
from app.services.payout.provider_paystack import paystack_charge_bank
from app.services.payout.provider_flutter import flutterwave_charge_bank
from app.services.payout.provider_monnify import monnify_charge
from app.handlers.wallet import Wallet


class PayoutError(Exception):
    pass


def provider_worker(provider, vendor, reference, vendor_amount):
    """
    Calls the correct payout provider dynamically.
    Ensures all required fields are present.
    """
    # Extract vendor info safely
    email = getattr(vendor, "email", None)
    name = getattr(vendor, "name", None)
    bank_code = getattr(vendor, "bank_code", None)
    account_number = getattr(vendor, "bank_account", None)

    # Required fields per provider
    if provider == "paystack":
        required = {"email": email, "bank_code": bank_code, "account_number": account_number}
    elif provider == "flutterwave":
        required = {"email": email, "bank_code": bank_code, "account_number": account_number, "tx_ref": reference}
    elif provider == "monnify":
        required = {"customer_name": name, "customer_email": email, "bank_code": bank_code, "account_number": account_number}
    else:
        raise ValueError(f"Unknown provider: {provider}")

    missing = [k for k, v in required.items() if v in [None, ""]]
    if missing:
        raise Exception(f"Provider {provider} missing required fields: {missing}")

    # Call provider
    if provider == "paystack":
        resp = paystack_charge_bank(email=email, amount=vendor_amount, bank_code=bank_code, account_number=account_number)
    elif provider == "flutterwave":
        resp = flutterwave_charge_bank(tx_ref=reference, amount=vendor_amount, bank_code=bank_code, account_number=account_number, email=email)
    elif provider == "monnify":
        resp = monnify_charge(account_number=account_number, bank_code=bank_code, amount=vendor_amount, customer_name=name, customer_email=email)

    return provider, resp


def process_vendor_payout(*, user_id: int, vendor_id: int, order_id: int, amount: float, provider: str):
    """
    Unified payout function for Paystack, Flutterwave, Monnify.
    Handles retrying fallback providers if the main fails.
    """
    
    vendor = Vendor.query.get(vendor_id)
    if not vendor:
        raise PayoutError("Vendor not found")

    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        raise PayoutError("Wallet not found")

    if wallet.balance < amount:
        raise PayoutError("Insufficient wallet balance")

    fee = getattr(vendor, "platform_fee", 700)
    vendor_amount = amount - fee
    reference = f"TRX-{uuid.uuid4().hex[:12]}"

    
    providers = ["paystack", "flutterwave", "monnify"]
    if provider in providers:
        providers.remove(provider)
        providers.insert(0, provider)

    used_provider = None
    provider_resp = None
    success = False
    i = 0

    while i < len(providers):
        current = providers[i]
        try:
            used_provider, provider_resp = provider_worker(current, vendor, reference, vendor_amount)

            # Normalize success check
            status = str(provider_resp.get("status")).lower() if provider_resp else "failed"
            if status in ["success", "true", "ok"]:
                success = True
                break
            else:
                i += 1
                continue
        except Exception:
            i += 1
            continue

    if not success:
        raise PayoutError("All providers failed")

    
    payment = Vendor_Payment(
        id=uuid.uuid4(),
        user_id=user_id,
        vendor_id=vendor_id,
        order_id=order_id,
        amount=amount,
        fee=fee,
        vendor_amount=vendor_amount,
        payment_gateway=used_provider,
        status="completed",
        vendor_bank_code=getattr(vendor, "bank_code", None),
        vendor_account_number=getattr(vendor, "bank_account", None),
        reference=reference,
        metadata=provider_resp,
        created_at=datetime.utcnow()
    )

    try:
        db.session.add(payment)
        wallet.debit(amount)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise PayoutError(f"Failed to record payment or debit wallet: {e}")


    return {
        "status": "success",
        "reference": reference,
        "amount": amount,
        "vendor_amount": vendor_amount,
        "fee": fee,
        "provider": used_provider,
        "provider_response": provider_resp,
        "wallet_balance": wallet.balance
    }
