import jwt
import datetime
from flask import current_app

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




