from flask import Blueprint, request, jsonify
from app.database.user_models import User
from app.utils.services import send_sms
from app.utils.jwt_tokens.generate_jwt import create_jwt_token
from app.utils.sms_processor.send_otp_login import send_otp_verification
from app.utils.sms_processor.verify_otp_login import verify_otp_code
from app.extensions import session_scope
import uuid

auth_bp_phone = Blueprint("auth_phone", __name__)


@auth_bp_phone.route("/auth/request-login-token", methods=["POST"])
def request_login_token():
    data = request.get_json() or {}
    phone = (data.get("phone") or "").strip()

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    if send_otp_verification(phone, context="login"):
        return jsonify({"message": "OTP sent successfully"}), 200

    return jsonify({"error": "Failed to send SMS"}), 500



@auth_bp_phone.route("/auth/verify-login-token", methods=["POST"])
def verify_login_token():
    data = request.get_json() or {}
    phone = (data.get("phone") or "").strip()
    otp = (data.get("otp") or "").strip()

    if not phone or not otp:
        return jsonify({"error": "Phone and OTP are required"}), 400

    if not verify_otp_code(phone, otp, context="login"):
        return jsonify({"error": "Invalid or expired OTP"}), 400

    with session_scope() as session:

        # -------------------------------
        # SAME LOGIC — just replaced db.session
        # -------------------------------
        user = session.query(User).filter_by(phone=phone).first()

        # If user exists → return JWT
        if user:
            jwt_token = create_jwt_token(
                user_id=user.id,
                username=user.name,
                password=user.password
            )
            return jsonify({
                "message": "Login successful",
                "token": jwt_token,
                "redirect": "/dashboard"
            }), 200

        # If user DOES NOT exist → create new one (same logic)
        new_user = User(
            phone=phone,
            email=str(uuid.uuid4()),
            name=str(uuid.uuid4()),
            google_id=str(uuid.uuid4()),
            facebook_id=str(uuid.uuid4()),
            last_ip=request.remote_addr,
            is_guest=False,
            extra_data={},
        )

        session.add(new_user)
        session.flush()  # ensures new_user.id exists

        jwt_token = create_jwt_token(
            user_id=new_user.id,
            username=new_user.name,
            password=new_user.password
        )

        return jsonify(
            {
                "message": "Login successful",
                "token": jwt_token,
                "redirect": "/dashboard",
            }
        ), 200

