import requests
from flask import current_app

class WhatsAppClient:
    def __init__(self, token: str, phone_number_id: str, api_version: str = "v18.0"):
        if not token or not phone_number_id:
            raise ValueError("WHATSAPP_TOKEN and META_PHONE_NUMBER_ID must be set")

        self.token = token
        self.phone_number_id = phone_number_id
        self.api_version = api_version
        self.base = f"https://graph.facebook.com/{self.api_version}"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def send_text(self, to: str, message: str, timeout: int = 10):
        url = f"{self.base}/{self.phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        resp = requests.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=timeout,
        )

        try:
            resp.raise_for_status()
        except Exception:
            current_app.logger.exception(
                "WhatsApp send failed: %s", resp.text
            )
            raise

        return resp.json()


def send_whatsapp_message(phone_number: str, notif_dict: dict):
    """
    Parameters MUST match:
    send_whatsapp_message.delay(vendor.phone_number, notif_dict)
    """

    message = (
        f"📦 New Order Notification\n\n"
        f"Order ID: {notif_dict.get('order_id')}\n"
        f"Type: {notif_dict.get('type')}\n"
        f"Total: ₦{notif_dict.get('payload', {}).get('total', 'N/A')}\n\n"
        f"Please check your dashboard for details."
    )

    client = WhatsAppClient(
        token=current_app.config["WHATSAPP_ACCESS_TOKEN"],
        phone_number_id=current_app.config["WHATSAPP_PHONE_NUMBER_ID"],
        api_version=current_app.config.get("WHATSAPP_API_VERSION", "v18.0"),
    )

    return client.send_text(phone_number, message)

