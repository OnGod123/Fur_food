from app.utils.jwt_tokens.generate_jwt import decode_jwt_token
from app.utils.jwt_tokens.generate_jwt import decode_rider_jwt
from app.utils.jwt_tokens.vendor_token import decode_vendor_jwt


class TokenIdentifyError(Exception):
    pass

def identify_token(token: str) -> dict:
    """
    Identify token owner (user | rider | vendor)
    Returns:
        {
            "type": "user" | "rider" | "vendor",
            "payload": {
                "id": <int>,
                ...original payload
            }
        }
    """

    # --------------------
    # 1️⃣ TRY USER TOKEN
    # --------------------
    payload = decode_jwt_token(token)
    if payload and payload.get("user_id"):
        payload["id"] = payload["user_id"]
        return {
            "type": "user",
            "payload": payload
        }

    # --------------------
    # 2️⃣ TRY RIDER TOKEN
    # --------------------
    payload = decode_rider_jwt(token)
    if payload and payload.get("rider_id"):
        payload["id"] = payload["rider_id"]
        return {
            "type": "rider",
            "payload": payload
        }

    # --------------------
    # 3️⃣ TRY VENDOR TOKEN
    # --------------------
    payload = decode_vendor_jwt(token)
    if payload and payload.get("vendor_id"):
        payload["id"] = payload["vendor_id"]
        return {
            "type": "vendor",
            "payload": payload
        }

    # --------------------
    # 4️⃣ FAIL
    # --------------------
    raise TokenIdentifyError("Unrecognized or invalid token")

