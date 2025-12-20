import hmac
import hashlib
import requests
from flask import current_app


class PaystarkProvider:
    BASE_URL = "https://api.paystack.co"

    def __init__(self):
        self.secret_key = current_app.config.get("PAYSTACK_SECRET_KEY")
        if not self.secret_key:
            raise RuntimeError("PAYSTACK_SECRET_KEY not set")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_payment(
        self,
        *,
        email: str,
        amount: float,
        reference: str,
        callback_url: str | None = None,
        metadata: dict | None = None,
    ):
        payload = {
            "email": email,
            "amount": int(amount * 100),  # NAIRA → KOBO
            "reference": reference,
        }

        if callback_url:
            payload["callback_url"] = callback_url

        if metadata:
            payload["metadata"] = metadata

        resp = requests.post(
            f"{self.BASE_URL}/transaction/initialize",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )

        data = resp.json()
        if not data.get("status"):
            raise RuntimeError(f"Paystack init failed: {data}")

        return {
            "payment_link": data["data"]["authorization_url"],
            "reference": data["data"]["reference"],
        }

    def verify_payment(self, reference: str) -> dict:
        resp = requests.get(
            f"{self.BASE_URL}/transaction/verify/{reference}",
            headers=self._headers(),
            timeout=15,
        )

        body = resp.json()
        if not body.get("status"):
            raise RuntimeError(f"Paystack verify failed: {body}")

        data = body["data"]

        return {
            "status": data["status"],          # success | failed
            "amount": data["amount"] / 100,    # KOBO → NAIRA
            "currency": data["currency"],
            "reference": data["reference"],
            "data": data,
        }

    @staticmethod
    def verify_webhook_signature(
        raw_body: bytes,
        signature: str,
        secret_key: str,
    ) -> bool:
        mac = hmac.new(secret_key.encode(), raw_body, hashlib.sha512)
        return hmac.compare_digest(mac.hexdigest(), signature)

