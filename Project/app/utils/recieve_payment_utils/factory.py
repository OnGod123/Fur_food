from app.utils.recieve_payment_utils.flutterwave import FlutterwaveProvider as flutterwave
from app.utils.recieve_payment_utils.paystark import PaystarkProvider as paystark
from app.utils.recieve_payment_utils.monnify import MonnifyProvider as monnify


def get_provider(name: str = "paystack"):
    name = (name or "paystack").lower().strip()

    if name == "paystark":
        return paystark()

    if name == "monnify":
        return monnify()
    
    if name == "flutterwave":
        return flutterwave()

    raise ValueError(f"Unsupported payment provider: {name}")

