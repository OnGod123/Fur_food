from flask import Blueprint, request, jsonify, g, url_for
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import r
from app.Database.multiple_order import OrderMultiple
from app.Database.order_single import OrderSingle
from app.Database.notifications import Notification
from app.Database.food_item import FoodItem
from app.Database.vendors_model import Vendor
from app.utils.jwt_tokens.authentication import token_required
from app.utils.emails.send_email import send_email_notification
from app.utils.whatsapp_utils import send_whatsapp_message
from app.utils.websocket_utils import send_notification_async
from app.utils.helpers.session import get_session
from app.utils.decorators import check_if_guest, vendor_must_be_open
from app.utils.jwt_tokens.generate_jwt import encode_order_id


multiple_order_bp = Blueprint(
    "multiple_order_bp",
    __name__,
    url_prefix="/Order_multiple"
)


@multiple_order_bp.route("/items", methods=["POST", "GET"])
@check_if_guest
@vendor_must_be_open
def multiple_order_handler():
    session = get_session()

    try:
        if request.method == "GET":
            order = (
                session.query(OrderMultiple)
                .filter_by(user_id=g.user.id)
                .order_by(OrderMultiple.created_at.desc())
                .first()
            )
            if not order:
                return jsonify({"order": None}), 200
            return jsonify({"order": order.to_dict()}), 200

        data = request.get_json() or {}
        items = data.get("items")

        if not items or not isinstance(items, list):
            return jsonify({"error": "Items list required"}), 400

        total = 0
        validated_items = []
        vendor_ids = set()

        for entry in items:
            required = ["item_id", "quantity", "price"]
            if not all(k in entry for k in required):
                return jsonify({"error": f"Invalid item data: {entry}"}), 400

            item = session.get(FoodItem, entry["item_id"])
            if not item:
                return jsonify(
                    {"error": f"Item {entry['item_id']} not found"}
                ), 404

            if float(entry["price"]) != float(item.price):
                return jsonify(
                    {"error": f"Price mismatch for item {entry['item_id']}"}
                ), 409

            validated_items.append(entry)
            total += entry["quantity"] * entry["price"]
            vendor_ids.add(item.vendor_id)

        # delete previous single orders
        session.query(OrderSingle).filter_by(
            user_id=g.user.id
        ).delete()

        order = OrderMultiple(
            user_id=g.user.id,
            items_data=validated_items,
            total=total,
            created_at=datetime.utcnow(),
        )

        session.add(order)
        session.commit()  # commit to get order.id

        notif_objects = []

        for vendor_id in vendor_ids:
            notif = Notification(
                user_id=g.user.id,
                vendor_id=vendor_id,
                order_id=str(order.id),
                type="new_multi_order",
                payload={
                    "vendors": list(vendor_ids),
                    "buyer_id": g.user.id,
                    "items": validated_items,
                },
            )
            session.add(notif)
            notif_objects.append(notif)

        session.commit()

        vendors_map = {
            v.id: v
            for v in (
                session.query(Vendor)
                .filter(Vendor.id.in_(vendor_ids))
                .all()
            )
        }

        for notif in notif_objects:
            notif_dict = notif.to_dict()
            vendor = vendors_map.get(notif.vendor_id)

            if not vendor:
                continue

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

        is_vendor = (
            session.query(Vendor)
            .filter_by(user_id=g.user.id)
            .first()
            is not None
        )

        if is_vendor:
            redirect_url = url_for(
                "notifications_bp.notify_vendor_from_order",
                order_id=order.id,
                event_type="new_multi_order",
                _external=True,
            )
            jwt_token = None
        else:
            jwt_token = encode_order_id(
                {"order_id": order.id}
            )
            redirect_url = url_for(
                "wallet_payment_bp.proceed_to_payment",
                order_id=order.id,
                total=total,
                token=jwt_token,
                _external=True,
            )

        return jsonify({
            "message": "Multiple-item order created successfully",
            "order_id": order.id,
            "redirect_url": redirect_url,
            "jwt": jwt_token,
            "total": total,
        }), 201

    except SQLAlchemyError as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()

