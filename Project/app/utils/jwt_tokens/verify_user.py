from flask import request, redirect, url_for, g
from functools import wraps
from app.utils.jwt_tokens.generate_jwt import decode_jwt_token
from app.Database.user_models import User
from app.extensions import session_scope

def verify_jwt_token(func):
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
            g.user = user

            if not user:
                return redirect(url_for("auth.signin"))

            
            return func(user, *args, **kwargs)

    return wrapper

