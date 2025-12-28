import jwt
import datetime
from flask import current_app
from app.extensions import r
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app


def set_user_state(user_id, is_guest=False):
    """
    Stores the current state of the user in Redis.
    """
    r.hset(f"user:{user_id}", "is_guest", str(is_guest).lower())  # "true" or "false"

def get_user_state(user_id):
    """
    Returns True if the user is currently a guest, False otherwise.
    """
    state = r.hget(f"user:{user_id}", "is_guest")
    if state is None:
        return False  
    return state.lower() 

def create_jwt_token(user_id, username, password_hash, auth_method):
    """
    Create a JWT token for a user.

    Parameters
    ----------
    user_id : int
    username : str
    password_hash : str
    auth_method : str
        One of "signup", "guest", "google", "phone", etc.

    Returns
    -------
    str
        Encoded JWT token
    """

    # Determine if user is a guest
    is_guest = True if auth_method.lower() == "guest" else False

    payload = {
        "user_id": user_id,
        "username": username,
        "password_hash": password_hash,
        "is_guest": is_guest,
        "auth_method": auth_method,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=10)
    }
    set_user_state(user_id, is_guest=False)
    token = jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")
    return token



def decode_jwt_token(token):
    try:
        decoded = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

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





