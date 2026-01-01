from flask import Blueprint, request, jsonify
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import r, session_scope
from app.Database.RiderAndStrawler import RiderAndStrawler
from app.Database.user_models import User
from app.utils.jwt_tokens.generate_jwt import generate_rider_jwt
from app.utils.emails.send_email import send_welcome_email


bp_rider_login = Blueprint("Blueprint_rider_bp", __name__, url_prefix="/rider")


@bp_rider_login.route("/login", methods=["POST"])
def login_rider():
    """
    Login a rider using email, username, and password.
    On first login, hash and store the password.
    Sends welcome email, generates JWT, and redirects rider to delivery page.
    """
    data = request.get_json() or {}

    email = data.get("email", "").lower().strip()
    username = data.get("username", "").strip()
    password = data.get("password")

    if not all([email, username, password]):
        return jsonify({"error": "email, username, and password are required"}), 400

    with session_scope() as session:
        # 1️⃣ Authenticate user
        user = session.query(User).filter_by(email=email, username=username).first()
        if not user:
            return jsonify({"error": "Invalid login credentials"}), 401

        # 2️⃣ Check Rider profile
        rider = session.query(RiderAndStrawler).filter_by(user_id=user.id).first()
        if not rider:
            return jsonify({"error": "User is not registered as a rider"}), 403

        # 3️⃣ Hash password if not set yet
        if not getattr(rider, "password_hash", None):
            rider.password_hash = generate_password_hash(password)
        else:
            # Verify password
            if not check_password_hash(rider.password_hash, password):
                return jsonify({"error": "Invalid rider credentials"}), 401

        # 4️⃣ Update rider status
        rider.status = "active"
        rider.is_available = True
        rider.last_update = datetime.utcnow()
        session.flush()

        # 5️⃣ Cache rider session in Redis
        r.set(f"rider:{user.email}:id", rider.id)

        # 6️⃣ Generate JWT (safe payload)
        rider_jwt = generate_rider_jwt(
            user_id=user.id,
            rider_id=rider.id,
            username=user.username
        )

        user_email = user.email
        user_username = user.username

    # 7️⃣ Send welcome email
    send_welcome_email(user_email, user_username)

    return jsonify({
        "message": "Rider login successful",
        "redirect_url": "/rider/delivery",
        "rider": rider.to_dict(),
        "rider_jwt": rider_jwt
    }), 200

