from flask import Blueprint, request, jsonify, redirect, url_for, current_app, render_template
from app.extensions import session_scope
from app.Database.user_models import User
from werkzeug.security import generate_password_hash
import re
from app.utils.jwt_tokens.generate_jwt import create_jwt_token

signup_bp = Blueprint("auth_signup", __name__, url_prefix="/create_account")

@signup_bp.route("signup", methods=["GET"])
def signup_get() -> str:
    return render_template("signup.html")

@signup_bp.route("signin", methods=["POST"])
def login_post():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        email_or_phone = (data.get("email") or data.get("phone") or "").strip()
        password = data.get("password")

        # ----------------- VALIDATION -----------------
        if not email_or_phone or not password:
            return jsonify({"error": "Missing required fields (email/phone and password)"}), 400

        # Allow login with either email or phone
        is_email = "@" in email_or_phone
        if is_email:
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email_or_phone):
                return jsonify({"error": "Invalid email format"}), 400
        else:
            # Very basic phone validation — adjust to your needs (e.g. Nigerian format)
            if not re.match(r"^\+?\d{8,15}$", email_or_phone):
                return jsonify({"error": "Invalid phone number format"}), 400

        # ----------------- DATABASE CHECK -----------------
        with session_scope() as session:
            # Try to find user by email or phone
            query_filter = (User.email == email_or_phone) if is_email else (User.phone == email_or_phone)
            user = session.query(User).filter(query_filter).first()

            if not user:
                return jsonify({
                    "error": "No account found with this email/phone",
                    "message": "Please sign up first",
                    "signup_url": url_for("auth_signup.signup_get")
                }), 404

            # Verify password
            if not check_password_hash(user.password_hash, password):
                return jsonify({"error": "Incorrect password"}), 401

            # Optional: update last login IP
            user.last_ip = request.remote_addr
            session.commit()  # or session.flush() if you prefer

            # ----------------- JWT TOKEN -----------------
            token = create_jwt_token(
                user_id=user.id,
                username=user.name,
                password=new_user.password
            )

            # ----------------- RESPONSE -----------------
            dashboard_url = url_for("user.dashboard", user_id=user.id)

            response = jsonify({
                "message": "Login successful",
                "user": user.to_dict() if hasattr(user, 'to_dict') else {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "phone": user.phone,
                },
                "token": token,
                "redirect": dashboard_url
            })
            response.status_code = 200

            if request.args.get("redirect") == "true":
                return redirect(dashboard_url)

            return response

    except Exception as e:
        current_app.logger.exception("Login error")
        return jsonify({"error": "Server error"}), 500


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
            session.flush()  

    
            token = create_jwt_token(
                user_id=new_user.id,
                username=new_user.name,
                password=new_user.password  
            )

            
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
