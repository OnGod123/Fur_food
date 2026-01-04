from flask import Blueprint, request, jsonify, g
from app.extensions import socketio, session_scope
from app.database.user_models import User
from app.merchants.Database.errand import Errand
from geopy.geocoders import Nominatim
from datetime import datetime
from functools import wraps
from flask import redirect, url_for
from app.utils.jwt_tokens.verify_user import verify_jwt_token

# ---------------- Blueprint ----------------
send_erand_bp = Blueprint("delivery_bp", __name__)
GLOBAL_ROOM = "all_participants"
geolocator = Nominatim(user_agent="rideshare_app")

# ---------------- Send Errand --------------
@send_erand_bp.route("/user/send_errand", methods=["POST"])
@verify_jwt_token
def send_errand():
    """
    User sends an errand.
    Input JSON:
    {
        "description": "<errand_description>",
        "destination": "<destination_address>",
        "mode": "manual" | "auto",
        "address": "<pickup_address>",       # manual
        "latitude": <float>,                 # auto
        "longitude": <float>                 # auto
    }
    """
    data = request.get_json() or {}

    description = data.get("description")
    destination = data.get("destination")
    mode = data.get("mode")

    if not description:
        return jsonify({"error": "Errand description required"}), 400
    if not destination:
        return jsonify({"error": "Destination required"}), 400
    if mode not in ("manual", "auto"):
        return jsonify({"error": "Mode must be 'manual' or 'auto'"}), 400

    # ---- Payload to broadcast ----
    user_send_errand = {
        "user_id": user.id,
        "user_name": getattr(user, "name", ""),
        "user_phone": getattr(user, "phone", ""),
        "description": description,
        "destination": destination,
        "created_at": datetime.utcnow().isoformat()
    }

    # ---- Pickup resolution ----
    if mode == "manual":
        address = data.get("address")
        if not address:
            return jsonify({"error": "Pickup address required for manual mode"}), 400

        user_send_errand.update({
            "pickup_address": address,
            "latitude": None,
            "longitude": None
        })

    else:
        lat = data.get("latitude")
        lng = data.get("longitude")

        if lat is None or lng is None:
            return jsonify({"error": "Coordinates required for auto mode"}), 400

        location = geolocator.reverse(f"{lat}, {lng}", language="en")
        if not location:
            return jsonify({"error": "Could not resolve pickup location"}), 400

        user_send_errand.update({
            "pickup_address": location.address,
            "latitude": lat,
            "longitude": lng
        })

    # ---- Persist errand ----
    with session_scope() as session:
        errand = Errand(
            user_id=user.id,
            description=description,
            pickup_address=user_send_errand["pickup_address"],
            pickup_latitude=user_send_errand["latitude"],
            pickup_longitude=user_send_errand["longitude"],
            destination=destination,
            created_at=datetime.utcnow()
        )
        session.add(errand)
        session.flush()
        errand_id = errand.id

    user_send_errand["errand_id"] = errand_id

    # ---- Broadcast globally ----
    socketio.emit(
        "new_errand_request",
        user_send_errand,
        room=GLOBAL_ROOM
    )

    return jsonify({
        "message": "Errand sent successfully",
        "errand_id": errand_id,
        "errand_data": user_send_errand
    }), 201

