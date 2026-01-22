
from flask import Blueprint, request, jsonify, g
from app.extensions import r, socketio, session_scope
from app.Database.user_models import User
from app.Database.  RiderAndStrawler import RiderAndStrawler
from app.Database.errand import Errand
from app.utils.jwt_tokens.verify_rider import verify_rider_jwt
from app.utils.jwt_tokens.verify_user import verify_jwt_token
from app.utils.whatsapp_utils.whatsapp_utils import send_whatsapp_message  

accept_errand_bp = Blueprint("accept_errand_bp", __name__)
GLOBAL_ROOM = "all_participants"


# ---------------- Rider Accept Errand ----------------
@accept_errand_bp.route("/rider/accept_errand", methods=["POST"])
@verify_rider_jwt
def accept_errand(rider):
    data = request.get_json() or {}
    errand_id = data.get("errand_id")
    if not errand_id:
        return jsonify({"error": "Missing errand_id"}), 400

    redis_key = f"errand:{errand_id}:accepted_by"
    if r.get(redis_key):
        return jsonify({"error": "Errand already accepted", "rider_id": r.get(redis_key).decode()}), 409

    r.set(redis_key, rider.id, ex=3600)
    r.set(f"errand:{errand_id}:status", "accepted", ex=3600)

    with session_scope() as session:
        errand = session.get(Errand, errand_id)
        if not errand:
            return jsonify({"error": "Errand not found"}), 404
        user = session.get(User, errand.user_id)

    # Notify user via SocketIO
    socketio.emit(
        "errand_accepted",
        {
            "errand_id": errand_id,
            "rider": {
                "id": rider.id,
                "name": getattr(rider.user, "name", ""),
                "phone": getattr(rider.user, "phone", "")
            }
        },
        room=f"user:{user.id}"
    )

    # WhatsApp notification
    send_whatsapp_message(
        user.phone,
        f"✅ Your errand has been accepted by {getattr(rider.user, 'name', '')}.\nErrand ID: {errand_id}"
    )

    return jsonify({"message": "Errand accepted"}), 200


# ---------------- Rider Decline Errand ----------------
@accept_errand_bp.route("/rider/decline_errand", methods=["POST"])
@verify_rider_jwt
def decline_errand(rider):
    data = request.get_json() or {}
    errand_id = data.get("errand_id")
    if not errand_id:
        return jsonify({"error": "Missing errand_id"}), 400

    redis_key = f"errand:{errand_id}:accepted_by"
    accepted_by = r.get(redis_key)
    if not accepted_by or int(accepted_by.decode()) != rider.id:
        return jsonify({"error": "You did not accept this errand"}), 403

    r.delete(redis_key)
    r.set(f"errand:{errand_id}:status", "pending", ex=3600)

    socketio.emit(
        "errand_back_to_pool",
        {"errand_id": errand_id},
        room=GLOBAL_ROOM
    )

    return jsonify({"message": "Errand declined"}), 200


# ---------------- User Unaccept Errand ----------------
@accept_errand_bp.route("/user/unaccept_errand", methods=["POST"])
@verify_jwt_token
def user_unaccept_errand(user):
    data = request.get_json() or {}
    errand_id = data.get("errand_id")
    if not errand_id:
        return jsonify({"error": "Missing errand_id"}), 400

    with session_scope() as session:
        errand = session.get(Errand, errand_id)
        if not errand or errand.user_id != user.id:
            return jsonify({"error": "Unauthorized"}), 403

    redis_key = f"errand:{errand_id}:accepted_by"
    accepted_by = r.get(redis_key)
    r.delete(redis_key)
    r.set(f"errand:{errand_id}:status", "pending", ex=3600)

    # Notify rider if assigned
    if accepted_by:
        socketio.emit(
            "errand_unaccepted_by_user",
            {"errand_id": errand_id},
            room=f"rider:{accepted_by.decode()}"
        )

    return jsonify({"message": "Errand unaccepted"}), 200

