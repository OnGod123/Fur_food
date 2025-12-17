from functools import wraps
from flask import jsonify, g
from app.database.user_models import User
from app.extensions import session_scope
from app.utils.sms_processor.twilo_sms import twilio_send_sms
from app.utils.sms_processor.send_otp_gammu import gammu_send_sms
def send_otp_payment(phone: str, context="payment", provider="twilio"):
    """
    Generate a payment OTP, store it in Redis, and send it using
    either Twilio or Gammu depending on the provider argument.

    Parameters
    ----------
    phone : str
        Phone number to send OTP to.
    context : str
        OTP purpose (default "payment").
    provider : str
        SMS gateway to use ("twilio" or "gammu"), default "twilio".

    Returns
    -------
    bool
        True if SMS sent successfully, False otherwise.
    """

    # Generate and store OTP in Redis with TTL = 5 minutes
    otp = generate_and_store_otp(phone, context=context, ttl=300)
    message = f"Your Gofood {context} verification code is {otp}. It expires in 5 minutes."

    if provider == "twilio":
        sid = twilio_send_sms(phone, message)
        return bool(sid)

    if provider == "gammu":
        return gammu_send_sms(phone, message)

    return False

def send_payment_otp_(context="payment", provider="twilio"):
    """
    Decorator that generates and sends an OTP before allowing a sensitive action.
    Does NOT run the wrapped function. Only sends OTP.
    Follows the same pattern as send_otp_verification.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            # g.user must already be set by verify_jwt_token
            user_id = g.user.id

            with session_scope() as session:
                user = session.get(User, user_id)

                if not user or not user.phone:
                    return jsonify({"error": "No phone number found for this user"}), 404

                # Generate and send OTP using same pattern as send_otp_verification
                sent = send_otp_payment(
                    phone=user.phone,
                    context=context,
                    provider=provider
                )

                if not sent:
                    return jsonify({"error": "Failed to send OTP"}), 500

            return jsonify({"message": f"OTP sent successfully for {context}"}), 200

        return wrapper
    return decorator

