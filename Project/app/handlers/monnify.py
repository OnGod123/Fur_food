

from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime
from app.extensions import session_scope
from app.Database.api_payment import Payment_api_database
from app.payments.factory import get_provider
from app.utils.jwt_tokens.authentication import token_required
from app.utils.helpers.tx_ref import generate_tx_ref
from app.models.wallet import Wallet

monnify_bp = Blueprint("monnify_bp", __name__,"/api/monnify")


@monnify_bp.route("/wallet/load", methods=["POST"])
@token_required
def initialize_monnify_payment():
    data = request.get_json(force=True) or {}
    amount = float(data.get("amount", 0))

    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    user = g.user
    tx_ref = generate_tx_ref(user.id)

    provider = get_provider("monnify")

    payment = provider.initialize_payment(
        user=user,
        amount=amount,
        payment_reference=tx_ref,
        redirect_url=current_app.config["PAYMENT_REDIRECT_URL"],
        metadata={"user_id": user.id},
    )

    with session_scope() as session:
        txn = Payment_api_database(
            provider="monnify",
            provider_txn_id=payment["transaction_reference"],
            tx_ref=tx_ref,
            amount=amount,
            currency="NGN",
            direction="in",
            target_user_id=user.id,
            meta={"source": "wallet_funding"},
            processed=False,
            verified_payment=False,
            created_at=datetime.utcnow(),
        )
        session.add(txn)

    return jsonify({
        "payment_link": payment["payment_link"],
        "reference": payment["reference"],
        "transaction_reference": payment["transaction_reference"],
    }), 201

@monnify_bp.route("/monnify/webhook", methods=["POST"])
def monnify_webhook():
    raw_body = request.get_data()
    signature = request.headers.get("monnify-signature")

    if not get_provider("monnify").verify_webhook_signature(
        raw_body,
        signature,
        current_app.config["MONNIFY_WEBHOOK_SECRET"],
    ):
        return "Invalid signature", 401

    payload = request.get_json(force=True)
    event_data = payload.get("eventData", {})
    payment_ref = event_data.get("paymentReference")

    if not payment_ref:
        return jsonify({"error": "Missing payment reference"}), 400

    provider = get_provider("monnify")
    result = provider.verify_payment(payment_ref)

    if result["status"] != "PAID":
        return jsonify({"status": "ignored"}), 200

    with session_scope() as session:
        txn = session.query(Payment_api_database).filter_by(
            tx_ref=payment_ref
        ).first()

        if not txn or txn.processed:
            return jsonify({"status": "already processed"}), 200

        wallet = session.query(Wallet).filter_by(
            user_id=txn.target_user_id
        ).with_for_update().first()

        if not wallet:
            return jsonify({"error": "Wallet not found"}), 404

        wallet.balance += result["amount"]

        txn.processed = True
        txn.verified_payment = True
        txn.processed_at = datetime.utcnow()

    return jsonify({"status": "wallet credited"}), 200


