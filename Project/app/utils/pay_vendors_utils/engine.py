import uuid      
from datetime import datetime
from flask import current_app
from app.extensions import Base
from app.Database.vendors_model import Vendor
from app.Database.vendor_payment import Vendor_Payment
from app.utils.pay_vendors_utils.paystark import paystark_charge_bank
from app.utils.pay_vendors_utils.flutterwave import flutterwave_charge_bank
from app.utils.pay_vendors_utils.monnify import monnify_charge_bank
from app.Database.wallet import Wallet


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


class PayoutError(Exception):
    pass


def process_vendor_payout(
    *,
    user_id: int,
    vendor,              # ✅ vendor passed in
    vendor_id: int,
    order_id: int,
    amount: float,
    provider: str
):
    """
    Unified payout function for Paystack, Flutterwave, Monnify.
    Handles retrying fallback providers if the main fails.
    """

    with session_scope() as session:

        # ---------------- Wallet ----------------
        wallet = session.query(Wallet).filter_by(user_id=user_id).first()
        if not wallet:
            raise PayoutError("Wallet not found")

        if wallet.balance < amount:
            raise PayoutError("Insufficient wallet balance")

        # ---------------- User (for narration) ----------------
        user = session.query(User).get(user_id)
        if not user:
            raise PayoutError("User not found")

        # ---------------- Fee ----------------
        fee = getattr(vendor, "platform_fee", 700)
        vendor_amount = amount - fee
        if vendor_amount <= 0:
            raise PayoutError("Vendor amount must be positive")

        # ---------------- Reference + narration ----------------
        reference = f"TRX-{order_id}-{uuid.uuid4().hex[:6]}"

        narration = (
            f"{user.name} ({user.email}) sent ₦{amount:,.0f} "
            f"for Order #{order_id}. Login to see details."
        )

        # ---------------- Provider priority ----------------
        providers = ["paystack", "flutterwave", "monnify"]
        if provider in providers:
            providers.remove(provider)
            providers.insert(0, provider)

        used_provider = None
        provider_resp = None
        success = False
        i = 0

        # ---------------- Fallback loop (UNCHANGED) ----------------
        while i < len(providers):
            current = providers[i]
            try:
                used_provider, provider_resp = provider_worker(
                    current,
                    vendor,
                    reference,
                    vendor_amount,
                    narration=narration
                )

                status = str(provider_resp.get("status")).lower() if provider_resp else "failed"
                if status in ["success", "successful", "true", "ok", "completed"]:
                    success = True
                    break

                i += 1
            except Exception:
                i += 1
                continue

        if not success:
            raise PayoutError("All providers failed")

        # ---------------- Persist payout ----------------
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

        session.add(payment)

        # ---------------- Debit wallet (same position as your logic) ----------------
        wallet.debit(amount)

        return {
            "status": "success",
            "reference": reference,
            "amount": amount,
            "vendor_amount": vendor_amount,
            "fee": fee,
            "provider": used_provider,
            "provider_response": provider_resp,
            "wallet_balance": wallet.balance,
        }

