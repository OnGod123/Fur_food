from functools import wraps
from flask import request, jsonify, g, current_app
import jwt
from datetime import datetime, timedelta
from app.extensions import session_scope
from app.Database.RiderAndStrawler import  RiderAndStrawler as Rider


def verify_rider_jwt(fn):
    """
    Decorator to protect endpoints for authenticated Riders.
    Decodes the Rider JWT and attaches the payload to g.rider.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Rider token required"}), 401

        token = auth.split(" ")[1]
        payload = decode_rider_jwt(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        rider_id = payload.get("rider_id")
        if not rider_id:
            return jsonify({"error": "Invalid token payload"}), 401

        with session_scope() as session:
            rider = session.get(Rider, rider_id)
            if not rider:
                return jsonify({"error": "Rider not found"}), 404

            # Attach payload and Rider instance to g
            g.rider = {
                "payload": payload,
                "instance": rider
            }

        return fn(*args, **kwargs)

    return wrapper


def generate_rider_jwt(user_id: int, rider_id: int, username: str, expires_minutes: int = 60) -> str:
    """
    Generate a JWT for a Rider.
    Payload includes user_id, rider_id, username, and timestamps.
    """
    payload = {
        "user_id": user_id,
        "rider_id": rider_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
        "iat": datetime.utcnow()
    }

    secret = current_app.config["JWT_SECRET_KEY"]
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def decode_rider_jwt(token: str) -> dict | None:
    """
    Decode a Rider JWT.
    Returns payload dict if valid, otherwise None.
    """
    secret = current_app.config["JWT_SECRET_KEY"]

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

