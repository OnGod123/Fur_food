from flask import Blueprint, request, jsonify, g, current_app
from app.extensions import socketio, session_scope, r  # r = Redis client
from app.Database.user_models import User
from app.Database.RiderAndStrawler import RiderAndStrawler
from app.Database.order_ride import  Ride_Order
from app.utils.jwt_tokens.verify_user import verify_jwt_token
from app.utils.jwt_tokens.verify_rider import verify_rider_jwt
from datetime import datetime

order_ride_bp = Blueprint("order_ride_bp", __name__)
GLOBAL_ROOM = "all_participants"


# ---------------- WhatsApp Notification ----------------
def send_whatsapp_message(phone_number: str, message: str):
    """
    Sends WhatsApp message using your WhatsApp client integration
    """
    from app.utils.whatsapp_client import WhatsAppClient  # your WhatsApp wrapper

    client = WhatsAppClient(
        token=current_app.config["WHATSAPP_ACCESS_TOKEN"],
        phone_number_id=current_app.config["WHATSAPP_PHONE_NUMBER_ID"],
        api_version=current_app.config.get("WHATSAPP_API_VERSION", "v18.0")
    )

    return client.send_text(phone_number, message)


# ---------------- Rider Accept Ride ----------------
@order_ride_bp.route("/rider/accept_ride", methods=["POST"])
@verify_rider_jwt
def accept_ride(rider):
    data = request.get_json() or {}
    ride_id = data.get("ride_id")
    if not ride_id:
        return jsonify({"error": "Missing ride_id"}), 400

    redis_key = f"ride:{ride_id}:accepted_by"
    if r.get(redis_key):
        return jsonify({"error": "Ride already accepted"}), 409

    # Mark ride accepted by this rider
    r.set(redis_key, rider.id, ex=3600)  # 1 hour expiry

    # Update RideShare DB status
    with session_scope() as session:
        ride = session.get(Ride_Order, ride_id)
        if not ride:
            return jsonify({"error": "Ride not found"}), 404

        ride.status = "accepted"
        ride.rider_id = rider.id
        ride.accepted_at = datetime.utcnow()

        # Get user info for WhatsApp
        user = session.get(User, ride.user_id)
        user_phone = getattr(user, "phone", None)

    # Notify user via SocketIO
    socketio.emit(
        "ride_accepted",
        {
            "ride_id": ride_id,
            "rider_id": rider.id,
            "rider_name": getattr(rider, "name", ""),
            "rider_phone": getattr(rider, "phone", "")
        },
        room=f"user:{ride.user_id}"
    )

    # Send WhatsApp notification
    if user_phone:
        message = (
            f"✅ Your ride has been accepted!\n"
            f"Rider: {getattr(rider, 'name', '')}\n"
            f"Phone: {getattr(rider, 'phone', '')}\n"
            f"Ride ID: {ride_id}"
        )
        send_whatsapp_message(user_phone, message)

    return jsonify({"message": "Ride accepted", "ride_id": ride_id}), 200


# ---------------- Rider Decline Ride ----------------
@order_ride_bp.route("/rider/decline_ride", methods=["POST"])
@verify_rider_jwt
def decline_ride(rider):
    data = request.get_json() or {}
    ride_id = data.get("ride_id")
    if not ride_id:
        return jsonify({"error": "Missing ride_id"}), 400

    redis_key = f"ride:{ride_id}:accepted_by"
    accepted_by = r.get(redis_key)

    if accepted_by and int(accepted_by.decode()) == rider.id:
        r.delete(redis_key)
        with session_scope() as session:
            ride = session.get(RideShare, ride_id)
            if ride:
                ride.status = "pending"
                ride.rider_id = None

        socketio.emit(
            "ride_declined",
            {"ride_id": ride_id, "rider_id": rider.id},
            room=GLOBAL_ROOM
        )
        return jsonify({"message": "Ride declined"}), 200
    else:
        return jsonify({"error": "You have not accepted this ride"}), 403


# ---------------- User Cancel Ride ----------------
@order_ride_bp.route("/user/cancel_ride", methods=["POST"])
@verify_jwt_token
def cancel_ride(user):
    data = request.get_json() or {}
    ride_id = data.get("ride_id")
    if not ride_id:
        return jsonify({"error": "Missing ride_id"}), 400

    redis_key = f"ride:{ride_id}:accepted_by"
    accepted_by = r.get(redis_key)

    with session_scope() as session:
        ride = session.get(RideShare, ride_id)
        if not ride or ride.user_id != user.id:
            return jsonify({"error": "Ride not found or unauthorized"}), 404

        ride.status = "cancelled"
        ride.rider_id = None
        ride.cancelled_at = datetime.utcnow()

    # Remove from Redis
    if accepted_by:
        r.delete(redis_key)

    # Notify rider if any
    if accepted_by:
        socketio.emit(
            "ride_cancelled",
            {"ride_id": ride_id, "user_id": user.id},
            room=f"rider:{accepted_by.decode()}"
        )

    # Notify all clients
    socketio.emit(
        "ride_unaccepted",
        {"ride_id": ride_id},
        room=GLOBAL_ROOM
    )

    return jsonify({"message": "Ride cancelled successfully"}), 200

