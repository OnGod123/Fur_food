import requests
from flask import current_app
from app.utils.recieve_payment.base_provider import PaymentProvider


class FlutterwaveProvider(PaymentProvider):
    """
    Flutterwave v3 – Standard Checkout
    POST /v3/payments
    GET  /v3/transactions/{id}/verify
    """

    def __init__(self):
        self.secret_key = current_app.config["FLUTTERWAVE_SECRET_KEY"]
        self.base_url = "https://api.flutterwave.com/v3"

        if not self.secret_key:
            raise RuntimeError("FLUTTERWAVE_SECRET_KEY not configured")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def initialize_payment(
        self,
        *,
        tx_ref: str,
        amount: float,
        user,
        currency: str = "NGN",
        redirect_url: str,
        payment_options: str = "card,ussd,banktransfer",
        payment_plan: int | None = None,
        link_expiration: str | None = None,
        session_duration: int = 30,
        max_retry_attempt: int = 5,
        customizations: dict | None = None,
        meta: dict | None = None,
    ) -> dict:
        """
        Returns:
        {
            "payment_link": "...",
            "tx_ref": "...",
            "provider_id": 123456
        }
        """

        payload = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": currency,
            "redirect_url": redirect_url,
            "payment_options": payment_options,
            "customer": {
                "email": user.email,
                "name": user.name,
                "phonenumber": user.phone,
            },
            "configuration": {
                "session_duration": session_duration,
            },
            "max_retry_attempt": max_retry_attempt,
            "meta": meta or {"user_id": str(user.id)},
        }

        if payment_plan:
            payload["payment_plan"] = payment_plan

        if link_expiration:
            payload["link_expiration"] = link_expiration

        if customizations:
            payload["customizations"] = customizations

        resp = requests.post(
            f"{self.base_url}/payments",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )

        data = resp.json()

        if data.get("status") != "success":
            raise RuntimeError(f"Flutterwave init failed: {data}")

        return {
            "payment_link": data["data"]["link"],
            "tx_ref": tx_ref,
            "provider_id": data["data"].get("id"),
        }

    def verify_payment(self, transaction_id: int) -> dict:
        resp = requests.get(
            f"{self.base_url}/transactions/{transaction_id}/verify",
            headers=self._headers(),
            timeout=15,
        )

        data = resp.json()

        if data.get("status") != "success":
            raise RuntimeError(f"Verification failed: {data}")

        tx = data["data"]

        return {
            "status": tx["status"].lower(),   # successful
            "amount": float(tx["amount"]),
            "currency": tx["currency"],
            "tx_ref": tx["tx_ref"],
            "provider_id": tx["id"],
            "data": tx,
        }

