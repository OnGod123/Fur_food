import hmac
import hashlib
from flask import Blueprint, request, abort, current_app
from sqlalchemy.orm import Session

from app.Database.user_models import User, 
from app.Database.wallet import Wallet

from app.extensions import session_scope  # wherever session_scope lives

paywebhook = Blueprint(
    "paywebhook",
    __name__,
    url_prefix="/webhook/paystack"
)


def verify_paystack_signature(req):
    signature = req.headers.get("X-Paystack-Signature")
    if not signature:
        return False

    secret = current_app.config.get("PAYSTACK_SECRET_KEY")
    if not secret:
        current_app.logger.error("PAYSTACK_SECRET_KEY not set")
        return False

    computed = hmac.new(
        secret.encode(),
        req.data,
        hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


@paywebhook.route("", methods=["POST"])
def handle_dva_webhook():
    # 1️⃣ Verify webhook signature
    if not verify_paystack_signature(request):
        abort(400, "Invalid Paystack signature")

    payload = request.json or {}
    authorization = payload.get("authorization", {})

    if not authorization:
        return "No authorization data", 400

    sender_account_number = authorization.get("sender_bank_account_number")
    sender_name = authorization.get("sender_name")
    sender_bank = authorization.get("sender_bank")
    narration = authorization.get("narration", "")
    amount = payload.get("amount", 0)

    if not sender_account_number or amount <= 0:
        return "Invalid payload", 400

    # Paystack sends amount in kobo
    amount = amount // 100

    # 2️⃣ DB logic using session_scope
    with session_scope() as session:
        user = (
            session.query(User)
            .filter(
                User.extra_data["bank_account_number"].astext
                == sender_account_number
            )
            .first()
        )

        if not user:
            current_app.logger.warning(
                f"Unknown sender account: {sender_account_number}"
            )
            return "User not found", 200  

        
        Wallet.credit(session, user.id, amount)

        current_app.logger.info(
            f"Wallet credited | user_id={user.id} | "
            f"amount={amount} | sender={sender_name} | "
            f"account={sender_account_number} | bank={sender_bank}"
        )

    return "OK", 200

