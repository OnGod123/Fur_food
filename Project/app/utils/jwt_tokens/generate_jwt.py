import jwt
import datetime
from flask import current_app
from app.extensions import r
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app


def create_jwt_token(user_id=None, username=None, password_hash=None, auth_method=""):
    payload = {
        "user_id": user_id,          # None for guest
        "username": username,        # None for guest
        "auth_method": auth_method,  # "guest" or ""
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=10)
    }

    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256"
    )

def is_guest_user(decoded):
    return decoded["auth_method"] == "guest"



def _get_serializer():
    """
    Create a serializer using the app SECRET_KEY
    """
    secret = current_app.config["SECRET_KEY"]
    return URLSafeTimedSerializer(secret, salt="order-id")


def encode_order_id(order_id: int | str) -> str:
    """
    Encode (sign) an order ID so it cannot be tampered with.
    """
    serializer = _get_serializer()
    return serializer.dumps({"order_id": order_id})


def decode_order_id(token: str, max_age: int | None = None) -> int | str:
    """
    Decode and verify an encoded order ID.

    :param token: encoded order id
    :param max_age: optional expiration time (seconds)
    """
    serializer = _get_serializer()

    try:
        data = serializer.loads(token, max_age=max_age)
        return data["order_id"]

    except SignatureExpired:
        raise ValueError("Order ID token expired")

    except BadSignature:
        raise ValueError("Invalid order ID token")



def generate_rider_jwt(user_id: int, rider_id: int, username: str, expires_minutes: int = 60) -> str:
    """
    Generate a JWT for a Rider.
    Payload includes user_id, rider_id, and username.
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
    Returns payload if valid, otherwise None.
    """
    secret = current_app.config["JWT_SECRET_KEY"]

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        # Token expired
        return None
    except jwt.InvalidTokenError:
        # Invalid token
        return None

