import base64
import hashlib
import hmac
import requests
from flask import current_app
from .base_provider import PaymentProvider


class MonnifyProvider(PaymentProvider):
    """
    Official Monnify payment provider
    """

    def __init__(self):
        self.api_key = current_app.config["MONNIFY_API_KEY"]
        self.secret_key = current_app.config["MONNIFY_SECRET_KEY"]
        self.contract_code = current_app.config["MONNIFY_CONTRACT_CODE"]
        self.base_url = current_app.config.get(
            "MONNIFY_BASE_URL", "https://sandbox.monnify.com"
        )

    # -------------------------
    # AUTH TOKEN
    # -------------------------
    def _get_access_token(self) -> str:
        credentials = f"{self.api_key}:{self.secret_key}"
        encoded = base64.b64encode(credentials.encode()).decode()

        resp = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            headers={"Authorization": f"Basic {encoded}"},
            timeout=15,
        )

        data = resp.json()
        if not data.get("requestSuccessful"):
            raise RuntimeError(f"Monnify auth failed: {data}")

        return data["responseBody"]["accessToken"]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    # -------------------------
    # INITIALIZE TRANSACTION
    # -------------------------
    def initialize_payment(
        self,
        user,
        amount: float,
        payment_reference: str,
        redirect_url: str,
        payment_methods=None,
        metadata=None,
    ) -> dict:

        payload = {
            "amount": amount,
            "customerEmail": user.email,
            "customerName": getattr(user, "name", "Customer"),
            "paymentReference": payment_reference,
            "paymentDescription": "Wallet funding",
            "currencyCode": "NGN",
            "contractCode": self.contract_code,
            "redirectUrl": redirect_url,
            "paymentMethods": payment_methods or ["CARD", "ACCOUNT_TRANSFER"],
            "metadata": metadata or {},
        }

        resp = requests.post(
            f"{self.base_url}/api/v1/merchant/transactions/init-transaction",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )

        data = resp.json()
        if not data.get("requestSuccessful"):
            raise RuntimeError(f"Monnify init failed: {data}")

        body = data["responseBody"]

        return {
            "reference": body["paymentReference"],
            "transaction_reference": body["transactionReference"],
            "payment_link": body["checkoutUrl"],
        }

    # -------------------------
    # VERIFY TRANSACTION
    # -------------------------
    def verify_payment(self, payment_reference: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/api/v2/transactions/{payment_reference}",
            headers=self._headers(),
            timeout=15,
        )

        data = resp.json()
        if not data.get("requestSuccessful"):
            raise RuntimeError(f"Monnify verify failed: {data}")

        body = data["responseBody"]

        return {
            "status": body["paymentStatus"],
            "amount": float(body["amountPaid"]),
            "reference": payment_reference,
        }

    # -------------------------
    # WEBHOOK SIGNATURE VERIFY
    # -------------------------
    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
        computed = hmac.new(
            secret.encode(),
            raw_body,
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

