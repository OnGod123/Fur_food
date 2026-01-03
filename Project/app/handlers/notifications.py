from flask import Blueprint, jsonify, g, request
from sqlalchemy.exc import SQLAlchemyError
from app.utils.jwt_tokens.generate_jwt import decode_order_id
from app.Database.order_single import OrderSingle
from app.Database.order_multiple import OrderMultiple
from app.utils.jwt_tokens.authentication import vendor_required

notifications_bp = Blueprint("notifications_bp", __name__)

@notifications_bp.route("/notifications/redirect", methods=["GET"])
@vendor_required
def notify_vendor_from_order():
    """
    Redirect handler for vendor notifications.
    Supports:
    - order_token (preferred, secure)
    - order_id (legacy/internal)
    """

    try:
        order_token = request.args.get("order_token")
        order_id = request.args.get("order_id")

        # -------------------------------
        # RESOLVE ORDER FROM URL
        # -------------------------------
        if order_token:
            payload = decode_order_id(order_token)

            if payload["vendor_id"] != g.vendor.id:
                return jsonify({"error": "no order notification yet"}), 403

            resolved_order_id = payload["order_id"]

        elif order_id:
            resolved_order_id = order_id

        else:
            return jsonify({"error": "Missing order reference"}), 400

        # -------------------------------
        # ORDER FROM NOTIFICATION
        # -------------------------------
        order_from_notification = OrderSingle.query.filter_by(
            id=resolved_order_id,
            vendor_id=g.vendor.id
        ).first()

        if not order_from_notification:
            return jsonify({"error": "Order not found"}), 404

        # -------------------------------
        # LATEST ORDER FOR VENDOR
        # -------------------------------
        latest_order = (
            OrderSingle.query
            .filter_by(vendor_id=g.vendor.id)
            .order_by(OrderSingle.created_at.desc())
            .first()
        )

        # -------------------------------
        # RESPONSE
        # -------------------------------
        return jsonify({
            "order_from_notification": order_from_notification.to_dict(),
            "latest_order": (
                latest_order.to_dict()
                if latest_order else None
            ),
            "order_type": "new_single_order"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


from flask import Blueprint, jsonify, g
from app.Database.notification import Notification
from app.Database.order_multiple import OrderMultiple
from app.utils.jwt_tokens.authentication import vendor_required

notifications_bp = Blueprint("notifications_bp", __name__)

@notifications_bp.route("/notifications/redirect", methods=["GET"])
@vendor_required
def notify_multiple_order():
    """
    MULTI-VENDOR notification resolver.

    Flow:
    1. Fetch latest notification for vendor
    2. Use notification.order_id
    3. Load OrderMultiple
    4. Filter items to this vendor
    """

    try:
        # ---------------------------------
        # 1. Latest notification for vendor
        # ---------------------------------
        notification = (
            Notification.query
            .filter_by(
                vendor_id=g.vendor.id,
                type="new_multi_order"
            )
            .order_by(Notification.created_at.desc())
            .first()
        )

        if not notification:
            return jsonify({"error": "No notifications found"}), 404

        # ---------------------------------
        # 2. Resolve order from notification
        # ---------------------------------
        order = OrderMultiple.query.filter_by(
            id=notification.order_id,
            user_id=notification.user_id
        ).first()

        if not order:
            return jsonify({"error": "Order not found"}), 404

        # ---------------------------------
        # 3. Filter items for this vendor
        # ---------------------------------
        vendor_items = [
            item for item in order.items_data
            if item.get("vendor_id") == g.vendor.id
        ]

        # ---------------------------------
        # 4. Response
        # ---------------------------------
        return jsonify({
            "notification_id": notification.id,
            "order_id": order.id,
            "buyer_id": order.user_id,
            "items": vendor_items,
            "order_type": "new_multi_order",
            "created_at": order.created_at.isoformat()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

