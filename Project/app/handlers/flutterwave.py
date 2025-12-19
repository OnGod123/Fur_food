from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime
from app.extensions import session_scope
from app.Database.api_payment import Payment_api_database
from app.payments.factory import get_provider
from app.utils.jwt_tokens.authentication import token_required
erom app.utils.helpers.tx_ref import generate_tx_ref

flutterwave_bp = Blueprint("flutterwave", __name__, url_prefix="/api/flutterwave")


@flutterwave_bp.route("/wallet/load", methods=["POST"])
@token_required
def initialize_payment():
    data = request.get_json(force=True)
    amount = data.get("amount")

    if not amount or float(amount) <= 0:
        return jsonify({"error": "Valid amount is required"}), 400

    user = g.user  
    tx_ref = generate_tx_ref(user.id)

    provider = get_provider("flutterwave")

    payment = provider.initialize_payment(
        tx_ref=tx_ref,
        amount=float(amount),
        user=user,
        redirect_url=current_app.config["Flutter_PAYMENT_REDIRECT_URL"],
        meta={"user_id": user.id}
    )

    with session_scope() as session:
        txn = Payment_api_database(
            provider="flutterwave",
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
        "tx_ref": tx_ref
    }), 201



@flutterwave_bp.route("/wallet/webhook", methods=["POST"])
def flutterwave_webhook():
    signature = request.headers.get("verif-hash")
    secret = current_app.config["FLUTTERWAVE_WEBHOOK_SECRET"]

    if signature != secret:
        return jsonify({"error": "Invalid signature"}), 401

    payload = request.get_json(force=True)
    data = payload.get("data", {})

    tx_ref = data.get("tx_ref")
    provider_txn_id = data.get("id")

    if not tx_ref or not provider_txn_id:
        return jsonify({"error": "Invalid payload"}), 400

    provider = get_provider("flutterwave")
    verification = provider.verify_payment(provider_txn_id)

    if verification["status"] != "successful":
        return jsonify({"error": "Payment not successful"}), 400

    with session_scope() as session:
        txn = (
            session.query(PaymentTransaction)
            .filter_by(tx_ref=tx_ref)
            .with_for_update()
            .first()
        )

        if not txn:
            return jsonify({"error": "Transaction not found"}), 404

        if txn.processed:
            return jsonify({"message": "Already processed"}), 200

        if verification["amount"] != txn.amount:
            raise RuntimeError("Amount mismatch")

        wallet = (
            session.query(Wallet)
            .filter_by(user_id=txn.target_user_id)
            .with_for_update()
            .first()
        )

        wallet.balance += verification["amount"]

        txn.provider_txn_id = provider_txn_id
        txn.verified_payment = True
        txn.processed = True
        txn.processed_at = datetime.utcnow()

        session.add(wallet)
        session.add(txn)

    return jsonify({"message": "Wallet funded"}), 200

