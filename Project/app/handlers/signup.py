from flask import Blueprint, request, jsonify, redirect, url_for, current_app, render_template
from app.extensions import db
from app.Database.user_models import User
from werkzeug.security import generate_password_hash
import re

signup_bp = Blueprint("auth_signup", __name__)


@signup_bp.route("/signup", methods=["GET"])
def signup_get() -> str:
    """
    Render the signup form.

    Returns
    -------
    str
        HTML template for the signup page.
    """
    return render_template("signup.html")


@signup_bp.route("/signup", methods=["POST"])
def signup_post():
    """
    JSON-based signup endpoint.

    Expected JSON payload:
        {
            "email": "user@example.com",
            "phone": "+1234567890",
            "password": "mypassword",
            "name": "John Doe",
            "metadata": { "referral": "friend", "country": "NG" }
        }

    Validates input, checks for duplicates, hashes password, creates a new user,
    commits to the database, and returns a JSON response with signup status.
    Optionally performs a redirect if query parameter 'redirect=true' is set.

    Returns
    -------
    Response
        JSON response containing:
        - message: Signup status
        - user: Dictionary representation of the newly created user
        - redirect: URL to dashboard
        Or performs HTTP redirect if requested.
    """
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

        if not email or not password or not name:
            return jsonify({"error": "Missing required fields (email, password, name)"}), 400

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({"error": "Invalid email format"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        existing_user: User = db.session.query(User).filter(
            (User.email == email) | (User.phone == phone)
        ).first()

        if existing_user:
            signin_url = url_for("auth_login.login_get")  # your login route
            return jsonify({
                "message": "Account already created. Please sign in.",
                "redirect": signin_url,
                "user_id": existing_user.id,
                "email": existing_user.email,
            }), 409
        # --------------------------

        password_hash: str = generate_password_hash(password)

        new_user: User = User(
            email=email,
            phone=phone or None,
            password_hash=password_hash,
            name=name,
            last_ip=ip_address,
            is_guest=False,
            metadata=metadata,
        )
        db.session.add(new_user)
        db.session.commit()

        dashboard_url: str = url_for("user.dashboard", user_id=new_user.id)
        token = generate_jwt(user_id=new_user.id, username=new_user.name)

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
        db.session.rollback()
        return jsonify({"error": "Server error", "details": str(e)}), 500