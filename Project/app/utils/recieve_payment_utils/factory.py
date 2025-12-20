from app.utils.recieve_payment.flutterwave import 


def get_provider(name: str = "paystack"):
    name = (name or "paystack").lower().strip()

    if name == "paystark":
        return Paystark()

    if name == "monnify":
        return Monnify()
    
    if name == "flutterwave"
        return flutterwave()

    raise ValueError(f"Unsupported payment provider: {name}")

