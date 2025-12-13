from app.utils.sms_processor.twilio_sms import twilio_send_sms
from app.utils.sms_processor. send_otp_gammu import send_sms as gammu_send_sms
from app.utils.sms_processor.otp_service import generate_and_store_otp



def send_otp_verification(phone: str, context="login", provider="twilio"):
    """
    Generate an OTP, store it in Redis, and send it using
    either Twilio or Gammu depending on the provider argument.

    Parameters
    ----------
    phone : str
        Phone number to send OTP to.
    context : str
        OTP purpose (e.g., "login", "payment", "reset_password").
    provider : str
        SMS gateway to use ("twilio" or "gammu").

    Returns
    -------
    bool
        True if SMS sent successfully, False otherwise.
    """

    # Generate and store OTP with TTL = 5 minutes
    otp = generate_and_store_otp(phone, context=context, ttl=300)
    message = f"Your Gofood {context} verification code is {otp}. It expires in 5 minutes."

    if provider == "twilio":
        sid = twilio_send_sms(phone, message)
        return bool(sid)

    if provider == "gammu":
        return gammu_send_sms(phone, message)

    return False
