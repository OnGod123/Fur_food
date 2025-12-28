from flask import Blueprint, jsonify, g, request
from sqlalchemy.exc import SQLAlchemyError
from app.utils.jwt_tokens.generate_jwt import decode_order_id
from app.merchants.Database.order_single import OrderSingle
from app.merchants.Database.order_multiple import OrderMultiple
from .decorators import vendor_required

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
        event_type = request.args.get("event_type")

        # -------------------------------
        # CASE 1: SECURE TOKEN FLOW
        # -------------------------------
        if order_token:
            payload = decode_order_id(order_token)

            if payload["vendor_id"] != g.vendor.id:
                return jsonify({"error": "Unauthorized order access"}), 403

            resolved_order_id = payload["order_id"]
            order_type = payload["order_type"]

        # -------------------------------
        # CASE 2: LEGACY / INTERNAL FLOW
        # -------------------------------
        elif order_id:
            resolved_order_id = order_id
            order_type = event_type

        else:
            return jsonify({"error": "Missing order reference"}), 400

        # -------------------------------
        # ORDER RESOLUTION
        # -------------------------------
        if order_type == "new_single_order":
            order = OrderSingle.query.filter_by(
                id=resolved_order_id,
                vendor_id=g.vendor.id
            ).first()

        else:  # multi-vendor order
            order = OrderMultiple.query.filter_by(
                id=resolved_order_id
            ).first()

        if not order:
            return jsonify({"error": "Order not found"}), 404

        # -------------------------------
        # RESPONSE (frontend can redirect)
        # -------------------------------
        return jsonify({
            "order": order.to_dict(),
            "order_type": order_type
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

