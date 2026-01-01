from functools import wraps
from flask import request, g, redirect, url_for, jsonify
from app.utils.jwt_tokens.generate_jwt import decode_jwt_token, is_guest_user

def check_if_guest(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Missing token"}), 401

        token = token.replace("Bearer ", "")
        decoded = decode_jwt_token(token)
        if not decoded:
            return jsonify({"error": "Invalid or expired token"}), 401

        g.user = decoded

        if is_guest_user(decoded):
            return redirect(url_for("profile_bp.update_profile"))

        return func(*args, **kwargs)

    return wrapper




