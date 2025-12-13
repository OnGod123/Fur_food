from flask import current_app
from twilio.rest import Client

_client = None


def twilio_send_sms(to_number: str, message: str) -> str | None:
    """
    Send SMS using Twilio.
    Returns Twilio SID on success, None on failure.
    """
    global _client

    try:
        # lazy-init client (one per worker)
        if _client is None:
            _client = Client(
                current_app.config["TWILIO_ACCOUNT_SID"],
                current_app.config["TWILIO_AUTH_TOKEN"],
            )

        msg = _client.messages.create(
            body=message,
            from_=current_app.config["TWILIO_FROM_NUMBER"],
            to=to_number,
        )
        return msg.sid

    except Exception:
        current_app.logger.exception("Twilio SMS failed")
        return None

