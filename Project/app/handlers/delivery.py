from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import r, socketio, session_scope  
from app.Database.delivery import Delivery
from app.Database.order_multiple import OrderMultiple
from app.Database.order_single import OrderSingle 
from app.Database.RiderAndStrawler import RiderAndStrawler as Rider
from app.Database.user_models import User

delivery_bp = Blueprint("delivery", __name__, url_prefix="/delivery")

GLOBAL_ROOM = "all_participants"


def broadcast_order_to_riders(latest_order, delivery, extra_address_info=None):
    if not latest_order or not delivery:
        return

    with session_scope() as session:
        user = session.get(User, latest_order.user_id)
        if not user:
            return

        items_list = []
        if getattr(latest_order, "items_data", None):
            items_list = latest_order.items_data
        elif getattr(latest_order, "item_data", None):
            items_list = [latest_order.item_data]

        order_data = {
            "order_id": latest_order.id,
            "user_id": latest_order.user_id,
            "user_name": getattr(user, "name", ""),
            "user_phone": getattr(user, "phone", ""),
            "delivery_address": delivery.address,
            "total": getattr(latest_order, "total", 0),
            "items": items_list,
            "created_at": str(latest_order.created_at),
        }

        if extra_address_info:
            order_data["address_update"] = extra_address_info

    socketio.emit("latest_order", order_data, room=GLOBAL_ROOM)


@delivery_bp.route("/delivery/<int:order_id>/location", methods=["GET", "POST"])
def manage_delivery_location(order_id):
    """
    Standard delivery handler for GET/POST updates.
    """
    with session_scope() as session:
        # Resolve order
        order = session.get(OrderSingle, order_id)
        if not order:
            order = session.get(OrderMultiple, order_id)
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Resolve delivery
        delivery = session.query(Delivery).filter_by(order_id=order.id).first()
        if not delivery:
            return jsonify({"error": "Delivery not found"}), 404

        if request.method == "GET":
            return jsonify({
                "delivery_id": delivery.id,
                "latest_order": {
                    "id": order.id,
                    "total": getattr(order, "total", 0),
                    "items": getattr(order, "items_data", getattr(order, "item_data", [])),
                    "created_at": str(order.created_at)
                },
                "delivery_address": delivery.address
            })

        # POST request — update address
        data = request.get_json() or {}
        mode = data.get("mode")
        extra_info = {"mode": mode}

        if mode == "manual":
            address = data.get("address")
            if not address:
                return jsonify({"error": "Missing address"}), 400
            delivery.address = address
            extra_info["resolved_address"] = address

        elif mode == "auto":
            lat = data.get("latitude")
            lng = data.get("longitude")
            if not lat or not lng:
                return jsonify({"error": "Missing coordinates"}), 400

            location = geolocator.reverse(f"{lat}, {lng}", language="en")
            if not location:
                return jsonify({"error": "Could not resolve address"}), 400

            delivery.address = location.address
            extra_info.update({
                "latitude": lat,
                "longitude": lng,
                "resolved_address": location.address
            })
        else:
            return jsonify({"error": "Invalid mode"}), 400

    # Commit is automatic at context exit
    broadcast_order_to_riders(order, delivery, extra_address_info=extra_info)

    return jsonify({
        "status": "success",
        "address": delivery.address,
        "extra_info": extra_info
    })



