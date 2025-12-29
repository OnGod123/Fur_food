from flask import Blueprint, request, jsonify, g, url_for
from datetime import datetime
import uuid

from app.extensions import session_scope
from app.Database.order_single import OrderSingle
from app.Database.order_multiple import OrderMultiple
from app.Database.wallet import Wallet
from app.Database.vendor_recieve_pay import Vendor_Payment
from app.utils.pay_vendors_utils.engine import process_vendor_payout
from app.utils.jwt_tokens.verify_user import verify_jwt_token
from app.utils.sms_processor.verify_otp_paymemt import verify_otp_payment
from app.utils.sms_processor.send_payment_otp import send_payment_otp_

wallet_payment_bp = Blueprint("wallet_payment_bp", __name__, url_prefix="/make-payment")

def handle_single_order(session, order, wallet):
    reference = str(uuid.uuid4())

    # Debit wallet
    Wallet.debit(session, g.user.id, order.total)
    order.is_paid = True
    order.paid_at = datetime.utcnow()

    payment = Vendor_Payment(
        id=str(uuid.uuid4()),
        user_id=g.user.id,
        vendor_id=order.vendor_id,
        order_id=order.id,
        amount=order.total,
        status="successful",
        payment_gateway="wallet",
        reference=reference,
        created_at=datetime.utcnow()
    )
    session.add(payment)

    # 🔹 Get vendor (REQUIRED)
    vendor = session.query(Profile).filter_by(id=order.vendor_id).first()
    if not vendor:
        raise Exception("Vendor not found")

    # Pay vendor
    process_vendor_payout(
        user_id=g.user.id,
        vendor_id=order.vendor_id,
        vendor=vendor,
        order_id=order.id,
        amount=order.total,
        provider="monnify"
    )

    return reference



def handle_multiple_order(session, order, wallet):
    
    items = getattr(order, "items_data", [])
    if len(items) > 15:
        return jsonify({"error": "Cannot pay more than 15 items in one transaction"}), 400

    Wallet.debit(session, g.user.id, order.total)
    order.is_paid = True
    order.paid_at = datetime.utcnow()

    for item in items:
        vendor_id = item.get("vendor_id")
        amount = item.get("price") * item.get("quantity")

        payment = Vendor_Payment(
            id=str(uuid.uuid4()),
            user_id=g.user.id,
            vendor_id=vendor_id,
            order_id=order.id,
            amount=amount,
            status="successful",
            payment_gateway="wallet",
            reference=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
        session.add(payment)

        # 🔹 Get vendor (REQUIRED)
        vendor = session.query(Vendor).filter_by(id=vendor_id).first()
        if not vendor:
            raise Exception(f"Vendor not found: {vendor_id}")

        process_vendor_payout(
            user_id=g.user.id,
            vendor_id=vendor_id,
            vendor=vendor,
            order_id=order.id,
            amount=amount,
            provider="monnify"
        )

    return str(uuid.uuid4())



# ---------------- Main Route ----------------
@wallet_payment_bp.route("/order/proceed-to-payment", methods=["GET"])
@verify_jwt_token
@send_payment_otp_
@verify_otp_payment(context="payment")
def proceed_to_payment():
    order_id = request.args.get("order_id")

    try:
        with session_scope() as session:

            # ---------------- Get Order ----------------
            order = None
            order_type = None
            if order_id:
                order_single = session.query(OrderSingle).filter_by(id=order_id, user_id=g.user.id).first()
                order_multiple = session.query(OrderMultiple).filter_by(id=order_id, user_id=g.user.id).first()
                order = order_single or order_multiple
                if not order:
                    return jsonify({"error": "Order not found"}), 404
                if getattr(order, "is_paid", False):
                    return jsonify({"error": "Order already paid"}), 400
                order_type = "single" if isinstance(order, OrderSingle) else "multiple"
            else:
                # get latest unpaid order
                order_single = session.query(OrderSingle).filter_by(user_id=g.user.id, is_paid=False).order_by(OrderSingle.created_at.desc()).first()
                order_multiple = session.query(OrderMultiple).filter_by(user_id=g.user.id, is_paid=False).order_by(OrderMultiple.created_at.desc()).first()
                if not order_single and not order_multiple:
                    return jsonify({"error": "No unpaid order found"}), 404
                if order_single and order_multiple:
                    order = order_single if order_single.created_at > order_multiple.created_at else order_multiple
                    order_type = "single" if order is order_single else "multiple"
                else:
                    order = order_single or order_multiple
                    order_type = "single" if order is order_single else "multiple"

            # ---------------- Lock Wallet ----------------
            wallet = session.query(Wallet).filter_by(user_id=g.user.id).with_for_update().first()
            if not wallet:
                return jsonify({"error": "Wallet not found"}), 404
            if wallet.balance < order.total:
                return jsonify({"error": "Insufficient balance"}), 400

            # ---------------- Handle Payment ----------------
            if order_type == "single":
                reference = handle_single_order(session, order, wallet)
            else:
                reference = handle_multiple_order(session, order, wallet)

        # ---------------- Delivery URL ----------------
        delivery_url = url_for("delivery_bp.start_delivery_process", order_id=order.id, _external=True)

        return jsonify({
            "message": "Payment completed successfully via wallet",
            "reference": reference,
            "order_type": order_type,
            "order_id": order.id,
            "amount": order.total,
            "wallet_balance": wallet.balance,
            "redirect_to_delivery": delivery_url
        }), 200

    except Exception as e:
        return jsonify({"error": "Wallet payment failed", "details": str(e)}), 500

