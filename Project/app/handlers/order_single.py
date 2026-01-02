from flask import Blueprint, request, jsonify, g, url_for
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import r
from app.Database.order_multiple import OrderMultiple
from app.Database.order_single import OrderSingle
from app.Database.notifications import Notification
from app.Database.food_item import FoodItem
from app.Database.vendors_model import Vendor
from app.utils.jwt_tokens.authentication import token_required
from app.utils.emails.send_email import send_email_notification
from app.utils.whatsapp_utils import send_whatsapp_message
from app.utils.websocket_utils.send_notification import send_notification_async
from app.extensions import get_session
from app.utils.vendors_utils.vendors_status import vendor_must_be_open
from app.utils.jwt_tokens.guest_token import check_if_guest
from app.utils.jwt_tokens.generate_jwt import encode_order_id


single_order_bp = Blueprint("single_order_bp", __name__, url_prefix="/order")


@single_order_bp.route("/single", methods=["POST", "GET"])
@check_if_guest
@vendor_must_be_open
def single_order_handler():
    try:
        # =======================
        # GET latest single order
        # =======================
        if request.method == "GET":
            order = (
                OrderSingle.query
                .filter_by(user_id=g.user.id)
                .order_by(OrderSingle.created_at.desc())
                .first()
            )

            if not order:
                return jsonify({"order": None}), 200

            return jsonify({"order": order.to_dict()}), 200

        # =======================
        # CREATE single order
        # =======================
        data = request.get_json() or {}
        required = ["item_id", "quantity", "price"]

        if not all(k in data for k in required):
            return jsonify({"error": "Missing required fields"}), 400

        item = FoodItem.query.get(data["item_id"])
        if not item:
            return jsonify({"error": "Item not found"}), 404

        if float(data["price"]) != float(item.price):
            return jsonify({"error": "Price mismatch"}), 409

        total = data["quantity"] * data["price"]

        # delete previous single orders
        OrderSingle.query.filter_by(
            user_id=g.user.id
        ).delete()

        order = OrderSingle(
            user_id=g.user.id,
            item_data=data,
            total=total,
            created_at=datetime.utcnow(),
            vendor_name=getattr(item, "vendor_name", "Unknown"),
            vendor_id = getattr(item, "vendor_name", "Unknown"),
            product_name=getattr(item, "name", "Unknown"),
        )

        db.session.add(order)
        db.session.commit()  # get order.id

        # =======================
        # Create notification
        # =======================
        notif = Notification(
            user_id=g.user.id,
            vendor_id=item.vendor_id,
            order_id=str(order.id),
            type="new_single_order",
            type="new_single_order",
            payload={
                "vendor_id": item.vendor_id,
                "buyer_id": g.user.id,
                "item": data,
            },
        )

        db.session.add(notif)
        db.session.commit()

        # =======================
        # Notify vendor
        # =======================
        notif_dict = notif.to_dict()
        vendor = Vendor.query.get(item.vendor_id)

        if vendor:
            r.publish("notifications", notif_dict)

            send_notification_async.delay(
                vendor.business_name,
                g.user.username,
                notif_dict
            )

            if vendor.phone_number:
                send_whatsapp_message.delay(
                    vendor.phone_number,
                    notif_dict
                )

            if vendor.email:
                send_email_notification.delay(
                    vendor.email,
                    notif_dict
                )

        # =======================
        # Redirect logic
        # =======================
        is_vendor = (
            Vendor.query
            .filter_by(user_id=g.user.id)
            .first()
            is not None
        )

        if is_vendor:
            redirect_url = url_for(
                "notifications.notify_vendor_from_order",
                order_id=order.id,
                event_type="new_single_order",
                _external=True,
            )
            order_token = None
        else:
            order_token = encode_order_id(
            order_id=order.id,
            vendor_id=item.vendor_id,
            order_type="new_single_order"
            )
            redirect_url = url_for(
                "payment.start_payment",
                order_id=order.id,
                total=order.total,
                token=order_token,
                _external=True,
            )

        return jsonify({
            "message": "Single-item order created successfully",
            "order_id": order.id,
            "redirect_url": redirect_url,
            "jwt": jwt_token,
            "total": order.total,
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

