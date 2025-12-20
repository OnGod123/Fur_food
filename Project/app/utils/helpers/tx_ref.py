import time
import secrets

def generate_tx_ref(user_id: int, provider: str = "FLW", env: str = "DEV") -> str:
    """
    Generate a Flutterwave-compatible transaction reference.

    Format:
    FLW-DEV-<user_id>-<unix_ts>-<random>

    Example:
    FLW-DEV-12-1703173379-a9f3
    """
    timestamp = int(time.time())
    rand = secrets.token_hex(2)  # 4 hex chars

    return f"{provider}-{env}-{user_id}-{timestamp}-{rand}"

