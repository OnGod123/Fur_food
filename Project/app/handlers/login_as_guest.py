from flask import Blueprint, request, jsonify
from app.Database.user_models import User
from app.utils.jwt_tokens.generate_jwt import create_jwt_token
import uuid
from app.extensions import session_scope

loginas_guest_bp = Blueprint("auth_bp", __name__)

@loginas_guest.route("/auth/login-guest", methods=["POST"])
def login_guest():
    """
    Allow a user to login as a guest. A new UUID is generated for both
    username and password if the user does not provide them.
    A JWT token is issued immediately.

    Returns
    -------
    200 : JSON
        {
            "message": "Guest login successful",
            "token": "<jwt_token>",
            "guest_id": "<uuid>",
            "redirect": "/dashboard"
        }
    """
    
    # Generate UUID for guest username and password
    client_ip = request.remote_addr

    # Generate guest UUID (only used if user does NOT exist)
    guest_uuid = str(uuid.uuid4())
    guest_name = f"Guest-{guest_uuid[:8]}"
    guest_password = guest_uuid

    with session_scope() as session:

        # Try to find an existing guest by IP
        existing_user = session.query(User).filter_by(last_ip=client_ip).first()

        # -----------------------------
        # 1️⃣ If guest already exists → return token
        # -----------------------------
        if existing_user:
            token = create_jwt_token(
                user_id=existing_user.id,
                username=existing_user.name,
                password=existing_user.password,
            )

            return jsonify({
                "message": "IP address registered (guest)",
                "token": token,
                "user_id": existing_user.id,
                "redirect": "/dashboard"
            }), 200

        # -----------------------------
        # 2️⃣ If guest does NOT exist → create new guest
        # -----------------------------
        user = User(
            phone=None,
            email=None,
            name=guest_name,
            password=guest_password,  # UUID stored as password
            google_id=None,
            facebook_id=None,
            last_ip=client_ip,
            is_guest=True,
            extra_data={},
        )

        session.add(user)
        session.flush()  # Ensure user.id exists

        # Generate JWT for new guest
        token = create_jwt_token(
            user_id=user.id,
            username=user.name,
            password=user.password,
        )

        return jsonify({
            "message": "Guest login successful",
            "token": token,
            "guest_id": guest_uuid,
            "redirect": "/dashboard",
        }), 200

