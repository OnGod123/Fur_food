from flask import request, redirect, url_for, g
from functools import wraps
from app.utils.jwt_tokens.generate_jwt import decode_jwt_token
from app.Database.user_models import User
from app.extensions import session_scope as session
from flask import request, g, jsonify

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


def vendor_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")

        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Vendor token required"}), 401

        token = auth.split(" ")[1]

        try:
            payload = decode_vendor_jwt(token)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        if payload.get("sub") != "vendor":
            return jsonify({"error": "Invalid vendor token"}), 403

        
        with session_scope() as session:
            vendor = session.get(Vendor, payload["vendor_id"])
            if not vendor:
                return redirect(url_for('auth.vendor'))

            # Attach vendor to global context
            g.vendor = vendor
            g.vendor_token_payload = payload

        return fn(*args, **kwargs)

    return wrapper

