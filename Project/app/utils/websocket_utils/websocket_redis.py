import json
from datetime import datetime
from flask import current_app
from app.extensions import r

MAX_CHAT_HISTORY = 500
CHAT_TTL = 24 * 3600  # 24h
REDIS_CHAT_LIST_KEY = "chat:messages:{room_id}"


def generate_shared_room(user_name: str, vendor_name: str) -> str:
    """Deterministic room id for user + vendor chat"""
    return "".join(sorted([user_name.lower(), vendor_name.lower()]))


def save_message_redis(room_id: str, msg: dict):
    """Append a message to Redis list for this room."""
    key = REDIS_CHAT_LIST_KEY.format(room_id=room_id)
    try:
        r.rpush(key, json.dumps(msg))
        r.ltrim(key, -MAX_CHAT_HISTORY, -1)
        r.expire(key, CHAT_TTL)
    except Exception:
        current_app.logger.exception(f"Failed saving message for room {room_id}")


def get_message_history(room_id: str, limit: int = 50):
    """Fetch last N messages for a room."""
    key = REDIS_CHAT_LIST_KEY.format(room_id=room_id)
    try:
        vals = r.lrange(key, -limit, -1)
        return [json.loads(v) for v in vals]
    except Exception:
        return []


def search_chat_room(user_name: str, room_name: str) -> str | None:
    room_id = generate_shared_room(user_name, room_name)
    key = REDIS_CHAT_LIST_KEY.format(room_id=room_id)

    try:
        if r.exists(key):
            return room_id
        return None
    except Exception:
        current_app.logger.exception("Failed searching chat room")
        return None
