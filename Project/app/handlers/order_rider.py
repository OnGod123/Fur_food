from flask import Blueprint, request, jsonify, g
from app.extensions import socketio, session_scope
from app.database.user_models import User
from app.merchants.Database.rideshare import RideShare
from geopy.geocoders import Nominatim
from datetime import datetime
from app.utils.jwt_tokens.verify_user import verify_jwt_token

order_ride_bp = Blueprint("delivery_bp", __name__)
GLOBAL_ROOM = "all_participants"

geolocator = Nominatim(user_agent="rideshare_app")

@order_ride_bp.route("/user/order_ride", methods=["POST"])
@verify_jwt_token
def order_ride(user):
    """
    User places a ride request.
    """

    data = request.get_json() or {}
    mode = data.get("mode")
    destination = data.get("destination")

    if not destination:
        return jsonify({"error": "Destination address required"}), 400

    user_send_coordinate = {
        "user_id": user.id,
        "username": getattr(user, "username", ""),
        "user_name": getattr(user, "name", ""),
        "phone": getattr(user, "phone", ""),
        "destination": destination,
        "created_at": str(datetime.utcnow())
    }

    # Resolve pickup location
    if mode == "manual":
        address = data.get("address")
        if not address:
            return jsonify({"error": "Pickup address required"}), 400

        user_send_coordinate.update({
            "pickup_address": address,
            "latitude": None,
            "longitude": None
        })

    elif mode == "auto":
        lat = data.get("latitude")
        lng = data.get("longitude")

        if lat is None or lng is None:
            return jsonify({"error": "Coordinates required"}), 400

        location = geolocator.reverse(f"{lat}, {lng}", language="en")
        if not location:
            return jsonify({"error": "Could not resolve pickup location"}), 400

        user_send_coordinate.update({
            "pickup_address": location.address,
            "latitude": lat,
            "longitude": lng
        })

    else:
        return jsonify({"error": "Invalid mode"}), 400

    # Store ride request
    with session_scope() as session:
        ride = RideShare(
            user_id=user.id,
            pickup_address=send_coordinate["pickup_address"],
            pickup_latitude=send_coordinate["latitude"],
            pickup_longitude=send_coordinate["longitude"],
            destination_address=destination,
            status="pending",
            created_at=datetime.utcnow()
        )
        session.add(ride)
        session.flush()
        ride_id = ride.id

    send_coordinate["ride_id"] = ride_id

    # Broadcast to riders
    socketio.emit(
        "new_ride_request",
        user_send_coordinate,
        room=GLOBAL_ROOM
    )

    return jsonify({
        "message": "Ride request placed successfully",
        "ride_id": ride_id,
        "user_send_coordinate": send_coordinate
    }), 201

