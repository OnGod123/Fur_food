from flask import request, redirect, url_for, g
from functools import wraps
from app.utils.jwt_tokens.generate_jwt import decode_jwt_token
from app.Database.user_models import User
from app.extensions import session_scope as session

def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return redirect(url_for("auth.signin"))

        token = auth_header.split(" ", 1)[1]

        payload = decode_jwt_token(token)
        if not payload:
            return redirect(url_for("auth.signin"))

        user_id = payload.get("user_id")
        if not user_id:
            return redirect(url_for("auth.signin"))

        with session_scope() as session:
            user = session.get(User, user_id)

            if not user:
                return redirect(url_for("auth.signin"))

            g.user = user   

        return func(*args, **kwargs)

    return wrapper

def vendor_required(func):
    """
    Ensures the request comes from a registered vendor.
    Decodes user JWT and checks if the user has a Vendor record.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing Authorization header"}), 401

        token = auth_header.split(" ")[1]

        try:
            payload = decode_jwt_token(token)
            user = session.query.get(payload.get("user_id"))
            if not user:
                return jsonify({"error": "User not found"}), 404

            vendor = session.query.filter_by(user_id=user.id).first()
            if not vendor:
                return jsonify({"error": "Only registered vendors can perform this action"}), 403

        except PermissionError as exc:
            return jsonify({"error": str(exc)}), 401

        g.user = user
        g.vendor = vendor
        return func(*args, **kwargs)

    return wrapper
