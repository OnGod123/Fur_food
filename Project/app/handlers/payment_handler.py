from flask import Blueprint, jsonify, url_for, g, request
from datetime import datetime
import uuid

from app.db import session_scope
from app.Database.order_single import OrderSingle
from app.Database.multiple_order import OrderMultiple
from app.Database.wallet import Wallet
from app.Database.vendor_recieve_pay import Vendor_Payment
from app.utils.pay_vendor_utils.engine import process_vendor_payout
from app.utils.jwt_tokens.verify_user import verify_jwt_token
from app.utils.sms_processor.verify_otp_paymemt import verify_otp_payment
from app.utils.sms_processor.send_payment_otp import send_payment_otp_

wallet_payment_bp = Blueprint("wallet_payment_bp", __name__, url_prefix="/make-payment")


@wallet_payment_bp.route("/order/proceed-to-payment", methods=["POST"])
@verify_jwt_token
@send_payment_otp_
@verify_otp_payment(context="payment")
def proceed_to_payment():

    order_id = request.args.get("order_id")

    try:
        # =====================================================
        # DB READ + VALIDATION
        # =====================================================
        with session_scope() as session:

            if order_id:
                single_order = (
                    session.query(OrderSingle)
                    .filter(
                        OrderSingle.id == order_id,
                        OrderSingle.user_id == g.user.id
                    )
                    .first()
                )

                multiple_order = (
                    session.query(OrderMultiple)
                    .filter(
                        OrderMultiple.id == order_id,
                        OrderMultiple.user_id == g.user.id
                    )
                    .first()
                )

                order = single_order or multiple_order

                if not order:
                    return jsonify({"error": "Order not found for this user"}), 404

                if order.is_paid:
                    return jsonify({
                        "error": "Order already paid. Please add a new order to cart."
                    }), 400

                order_type = "single" if isinstance(order, OrderSingle) else "multiple"

            else:
                single_order = (
                    session.query(OrderSingle)
                    .filter(
                        OrderSingle.user_id == g.user.id,
                        OrderSingle.is_paid.is_(False)
                    )
                    .order_by(OrderSingle.created_at.desc())
                    .first()
                )

                multiple_order = (
                    session.query(OrderMultiple)
                    .filter(
                        OrderMultiple.user_id == g.user.id,
                        OrderMultiple.is_paid.is_(False)
                    )
                    .order_by(OrderMultiple.created_at.desc())
                    .first()
                )

                if not single_order and not multiple_order:
                    return jsonify({
                        "error": "No unpaid order found. Please add items to cart."
                    }), 404

                if single_order and multiple_order:
                    order = single_order if single_order.created_at > multiple_order.created_at else multiple_order
                    order_type = "single" if order is single_order else "multiple"
                elif single_order:
                    order = single_order
                    order_type = "single"
                else:
                    order = multiple_order
                    order_type = "multiple"

            wallet = (
                session.query(Wallet)
                .filter(Wallet.user_id == g.user.id)
                .with_for_update()
                .first()
            )

            if not wallet:
                return jsonify({"error": "Wallet not found"}), 404

            if wallet.balance < order.total:
                return jsonify({
                    "error": "Insufficient balance. Please fund your wallet."
                }), 400

            # =====================================================
            # ATOMIC PAYMENT + VENDOR PAYOUT (RACE WINDOW REMOVED)
            # =====================================================
            reference = str(uuid.uuid4())

            # 1️⃣ Debit wallet
            Wallet.debit(session, g.user.id, order.total)

            # 2️⃣ Mark order as paid
            order.is_paid = True
            order.paid_at = datetime.utcnow()

            # 3️⃣ Create payment record
            payment = Vendor_Payment(
                id=str(uuid.uuid4()),
                user_id=g.user.id,
                vendor_id=getattr(order, "vendor_id", None),
                order_id=order.id,
                amount=order.total,
                status="successful",
                payment_gateway="wallet",
                reference=reference,
                created_at=datetime.utcnow(),
            )
            session.add(payment)

            # 4️⃣ Pay vendor inside same transaction
            process_vendor_payout(
                user_id=g.user.id,
                vendor_id=getattr(order, "vendor_id", None),
                order_id=order.id,
                amount=order.total,
                provider="monnify"
            )

        # =====================================================
        # DELIVERY URL (outside transaction)
        # =====================================================
        delivery_url = url_for(
            "delivery_bp.start_delivery_process",
            order_id=order.id,
            _external=True
        )

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
        return jsonify({
            "error": "Wallet payment failed",
            "details": str(e)
        }), 500


