"""
Google OAuth authentication blueprint.

This module handles Google OAuth login flow, user creation,
signin logging, JWT creation, and session management.
"""

from flask import (
    Blueprint,
    request,
    redirect,
    url_for,
    jsonify,
    make_response,
    current_app,
)
from app.extensions import oauth, r, session_scope
from app.database.user_models import User
from app.database.signinmodels import Signin
from authlib.integrations.flask_client import OAuth
from app.utils.jwt_tokens.generate_jwt import create_jwt_token
import uuid
import os

auth_bp = Blueprint("auth", __name__)

google = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", "your-google-client-id"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "your-google-client-secret"),
    access_token_url="https://oauth2.googleapis.com/token",
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    api_base_url="https://www.googleapis.com/oauth2/v2/",
    userinfo_endpoint="https://www.googleapis.com/oauth2/v2/userinfo",
    client_kwargs={"scope": "openid email profile"},
)


@auth_bp.route("/google/login")
def google_login():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/google/callback")
def google_callback():
    token = google.authorize_access_token()
    user_info = google.get("userinfo").json()

    user_email = user_info.get("email")
    user_name = user_info.get("name")
    user_google_id = user_info.get("id")
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent")

    if not user_email:
        return jsonify({"error": "Unable to retrieve Google account email"}), 400

    # ---------------- DATABASE SCOPE ----------------
    with session_scope() as session:
        user = session.query(User).filter_by(email=user_email).first()

        if user:
            jwt_token = create_jwt_token(
                user_id=user.id,
                username=user.name,
                password=user.password
            )
            return jsonify({
                "message": "IP address registered (guest)",
                "token": jwt_token,
                "user_id": user.id,
                "redirect": "/dashboard"
            }), 200

        # User does not exist → create
        # Fill password with UUID if not available
        user_password = str(uuid.uuid4())

        user = User(
            email=user_email,
            name=user_name,
            google_id=user_google_id,
            password=user_password,
            is_guest=False,
        )
        session.add(user)
        session.flush()  # ensure user.id is available

        signin_log = Signin(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            method="google",
            success=True,
        )
        session.add(signin_log)
        # commit happens automatically at context exit

        jwt_token = create_jwt_token(
            user_id=user.id,
            username=user.name,
            password=user.password
        )

        # ---------------- REDIS SESSION ----------------
        r.setex(
            f"session:{user.id}",
            current_app.config["SESSION_EXPIRE"],
            "active",
        )

    # ---------------- RETURN COOKIE + REDIRECT ----------------
    response = make_response(redirect("/dashboard"))
    response.set_cookie(
        "jwt",
        jwt_token,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=current_app.config["SESSION_EXPIRE"],
    )

    return response

