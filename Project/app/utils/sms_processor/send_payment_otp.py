from functools import wraps
from flask import jsonify, g
from app.database.user_models import User
from app.utils.sms_providers import send_payment_otp as send_sms_otp
from app.extensions import session_scope


def send_payment_otp(context="payment"):
    """
    Decorator that sends an OTP before allowing a sensitive action.
    Does NOT run the wrapped function.
    Only sends OTP.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            # g.user must already be set by verify_jwt_token
            user_id = g.user.id

            with session_scope() as session:
                user = session.get(User, user_id)

                if not user or not user.phone:
                    return jsonify(
                        {"error": "No phone number found for this user"}
                    ), 404

                sent = send_sms_otp(user.phone)

                if not sent:
                    return jsonify(
                        {"error": "Failed to send OTP"}
                    ), 500

            return jsonify(
                {"message": f"OTP sent successfully for {context}"}
            ), 200

        return wrapper
    return decorator
i
