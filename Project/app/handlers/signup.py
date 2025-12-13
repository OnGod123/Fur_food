from flask import Blueprint, request, jsonify, redirect, url_for, current_app, render_template
from app.extensions import session_scope
from app.Database.user_models import User
from werkzeug.security import generate_password_hash
import re
from app.utils.jwt_tokens.generate_jwt import create_jwt_token


signup_bp = Blueprint("auth_signup", __name__, url_prefix="/create_account")


@signup_bp.route("/signup", methods=["GET"])
def signup_get() -> str:
    return render_template("signup.html")


@signup_bp.route("/signup", methods=["POST"])
def signup_post():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        email: str = (data.get("email") or "").strip().lower()
        phone: str = (data.get("phone") or "").strip()
        password: str = data.get("password")
        name: str = (data.get("name") or "").strip()
        metadata: dict = data.get("metadata") or {}
        ip_address: str = request.remote_addr

        # ----------------- VALIDATION -----------------
        if not email or not password or not name:
            return jsonify({"error": "Missing required fields (email, password, name)"}), 400

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({"error": "Invalid email format"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        # ----------------- DATABASE -----------------
        with session_scope() as session:

            # Check if user exists
            existing_user = session.query(User).filter(
                (User.email == email) | (User.phone == phone)
            ).first()

            if existing_user:
                signin_url = url_for("auth_login.login_get")
                return jsonify({
                    "message": "Account already created. Please sign in.",
                    "redirect": signin_url,
                    "user_id": existing_user.id,
                    "email": existing_user.email,
                }), 409

            # Hash password
            password_hash = generate_password_hash(password)

            # Create new user
            new_user = User(
                email=email,
                phone=phone or None,
                password_hash=password_hash,
                name=name,
                last_ip=ip_address,
                is_guest=False,
                metadata=metadata,
            )

            session.add(new_user)
            session.flush()  # ensures new_user.id is available

            # ----------------- JWT TOKEN -----------------
            # EXACTLY YOUR REQUIRED FORMAT
            token = create_jwt_token(
                user_id=new_user.id,
                username=new_user.name,
                password=new_user.password  # If this field doesn't exist, use new_user.password_hash
            )

            # ----------------- RESPONSE -----------------
            dashboard_url = url_for("user.dashboard", user_id=new_user.id)

            response = jsonify({
                "message": "Signup successful",
                "user": new_user.to_dict(),
                "redirect": dashboard_url,
                "token": token
            })
            response.status_code = 201

            if request.args.get("redirect") == "true":
                return redirect(dashboard_url)

            return response

    except Exception as e:
        current_app.logger.exception("Signup error")
        return jsonify({"error": "Server error"}), 500

