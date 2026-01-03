from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import r, socketio, session_scope
from app.utils.jwt_tokens.verify_rider import 
from app.Database.order_multiple import OrderMultiple
from app.Database.order_single import OrderSingle
from app.Database.RiderAndStrawler import RiderAndStrawler as Rider
from app.Database.user_models import User

accept_order_bp =  Blueprint("Rider_bp", __name__)

@accept_order_bp.route("/rider/unaccept_order", methods=["POST"])
@rider_required
def unaccept_order():
    """
    Rider can unmark an order if:
      - They accepted it in Redis
      - OR are assigned to the delivery
    """
    data = request.get_json()
    order_id = data.get("order_id")
    if not order_id:
        return jsonify({"error": "Missing order_id"}), 400

    rider_instance = g.rider["instance"]
    rider_id = str(rider_instance.id)

    redis_key = f"order:{order_id}:accepted_by"
    accepted_by = r.get(redis_key)

    allow_unaccept = False

    if accepted_by and accepted_by.decode() == rider_id:
        allow_unaccept = True
    else:
        with session_scope() as session:
            delivery = session.query(Delivery).filter_by(order_id=order_id, rider_id=rider_instance.id).first()
            if delivery:
                allow_unaccept = True

    if not allow_unaccept:
        return jsonify({"error": "You cannot unmark this order"}), 403

    if accepted_by:
        r.delete(redis_key)

    return jsonify({"message": "Order unmarked"}), 200

@accept_order_bp.route("/rider/accept_order", methods=["POST"])
@rider_required
def accept_order():
    data = request.get_json()
    order_id = data.get("order_id")
    if not order_id:
        return jsonify({"error": "Missing order_id"}), 400

    rider_instance = g.rider["instance"]
    rider_id = rider_instance.id

    redis_key = f"order:{order_id}:accepted_by"
    accepted_by = r.get(redis_key)
    if accepted_by:
        return jsonify({
            "error": "Order already accepted",
            "rider_id": accepted_by.decode()
        }), 409

    r.set(redis_key, rider_id)
    r.expire(redis_key, 60 * 60)

    # Get user_id to notify (from Redis or DB fallback)
    user_id = r.get(f"order:{order_id}:user_id")
    if not user_id:
        with session_scope() as session:
            order = session.get(OrderSingle, order_id) or session.get(OrderMultiple, order_id)
            if not order:
                return jsonify({"error": "Order not found"}), 404
            user_id = str(order.user_id).encode()
            r.set(f"order:{order_id}:user_id", user_id)

    user_info = {
        "rider_id": rider_instance.id,
        "rider_name": getattr(rider_instance.user, "name", ""),
        "rider_phone": getattr(rider_instance.user, "phone", "")
    }

    socketio.emit(
        "order_accepted",
        {"order_id": order_id, "rider": user_info},
        room=f"user:{user_id.decode()}"
    )

    return jsonify({"message": "Order accepted", "rider_id": rider_id}), 200


@aceept_order_bp.route("/user/unaccept_order", methods=["POST"])
@user_required
def user_unaccept_order():
    """
    The person who placed the order can cancel/unaccept the ride.
    """
    data = request.get_json()
    order_id = data.get("order_id")
    if not order_id:
        return jsonify({"error": "Missing order_id"}), 400

    user_instance = g.user["instance"]

    with session_scope() as session:
        # Check if the user owns the order
        order = session.get(OrderSingle, order_id) or session.get(OrderMultiple, order_id)
        if not order:
            return jsonify({"error": "Order not found"}), 404

        if order.user_id != user_instance.id:
            return jsonify({"error": "You cannot unmark this order"}), 403

    # Remove accepted_by in Redis if any
    redis_key = f"order:{order_id}:accepted_by"
    r.delete(redis_key)

    # Notify riders in GLOBAL_ROOM that order is now unaccepted/cancelled
    socketio.emit(
        "order_unaccepted",
        {"order_id": order_id},
        room="all_participants"
    )

    return jsonify({"message": "Order unaccepted/cancelled by user"}), 200
