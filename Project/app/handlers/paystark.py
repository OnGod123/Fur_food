from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime

from app.extensions import session_scope
from app.Database.api_payment import Payment_api_database
from app.utils.recieve_payment_utils.factory import get_provider
from app.utils.jwt_tokens.authentication import token_required
from app.utils.helpers.tx_ref import generate_tx_ref

paystark_bp = Blueprint("paystack", __name__, url_prefix="/api/paystark")



@paystark_bp.route("/wallet/load", methods=["POST"])
@token_required
def initialize_payment():
    data = request.get_json(force=True)
    amount = data.get("amount")

    if not amount or float(amount) <= 0:
        return jsonify({"error": "Valid amount is required"}), 400

    user = g.user
    tx_ref = generate_tx_ref(user.id)

    provider = get_provider("paystack")

    payment = provider.initialize_payment(
        email=user.email,
        amount=float(amount),
        reference=tx_ref,
        callback_url=current_app.config.get("PAYSTACK_REDIRECT_URL"),
        metadata={"user_id": user.id},
    )

    with session_scope() as session:
        txn = Payment_api_database(
            provider="paystack",
            provider_txn_id=None,
            tx_ref=tx_ref,
            amount=float(amount),
            currency="NGN",
            direction="in",
            target_user_id=user.id,
            meta={"email": user.email},
            processed=False,
            verified_payment=False,
            created_at=datetime.utcnow(),
        )
        session.add(txn)

    return jsonify({
        "payment_link": payment["payment_link"],
        "tx_ref": tx_ref,
    }), 201


@paystark_bp.route("/wallet/webhook", methods=["POST"])
def paystark_webhook():
    raw_body = request.get_data()
    signature = request.headers.get("X-Paystack-Signature")

    if not PaystackProvider.verify_webhook_signature(
        raw_body,
        signature,
        current_app.config["PAYSTACK_SECRET_KEY"],
    ):
        return "Invalid signature", 401

    payload = request.get_json(force=True)
    event = payload.get("event")
    data = payload.get("data", {})

    if event != "charge.success":
        return "Ignored", 200

    reference = data.get("reference")

    with session_scope() as session:
        txn = (
            session.query(Payment_api_database)
            .filter_by(tx_ref=reference)
            .with_for_update()
            .first()
        )

        if not txn or txn.processed:
            return "OK", 200

        wallet = (
            session.query(Wallet)
            .filter_by(user_id=txn.target_user_id)
            .with_for_update()
            .first()
        )

        wallet.balance += data["amount"] / 100

        txn.provider_txn_id = data["id"]
        txn.processed = True
        txn.verified_payment = True
        txn.processed_at = datetime.utcnow()

        session.add(wallet)
        session.add(txn)

    return "OK", 200

