import json
from datetime import datetime
from flask import request, g
from flask_socketio import Namespace, emit, join_room
from app.extensions import socketio, r as redis
from app.utils.jwt_tokens.identify_token import identify_token
from app.Database.user_models import User
from app.Database. RiderAndStrawler import  RiderAndStrawler as  Rider
from app.Database.vendors_model import Vendor
from app.extensions import session_scope

class TokenIdentifyError(Exception):
    pass

def participant_exists(username: str) -> bool:
    with session_scope() as session:
        return (
            session.query(User).filter_by(username=username).first()
            or session.query(Rider).filter_by(username=username).first()
            or session.query(Vendor).filter_by(username=username).first()
        ) is not None


class PrivateNamespace(Namespace):
    namespace = "/private"

    # ---------- CONNECT ----------
    def on_connect(self):
        token = request.args.get("token")
        user = request.args.get("user")
        peer = request.args.get("peer")

        if not token or not user or not peer:
            return False

        # Identify token owner
        try:
            identity = identify_token(token)
        except TokenIdentifyError:
            return False

        username = identity["payload"].get("username")
        if username != user:
            return False  # token owner must match URL user

        # Validate both participants exist
        if not participant_exists(user) or not participant_exists(peer):
            return False

        # Canonical room
        u1, u2 = sorted([user, peer])
        room = f"private:{u1}:{u2}"

        # Store context
        g.client_id = identity["payload"]["id"]
        g.client_type = identity["type"]
        g.username = username
        g.room = room

        join_room(room)

        emit("connected", {
            "room": room,
            "peer": peer
        })


    def on_send_private_message(self, data):
        message = data.get("message")
        room = g.get("room")

        if not message or not room:
            emit("error", {"message": "Invalid message"})
            return

        payload = {
            "sender_id": g.client_id,
            "sender_type": g.client_type,
            "sender_name": g.username,
            "message": message,
            "room": room,
            "ts": datetime.utcnow().isoformat() + "Z"
        }

        redis.rpush(
            f"chat:private:{room}",
            json.dumps(payload)
        )

        emit("receive_private_message", payload, room=room)

    def on_send_private_message(self, data):
        message = data.get("message")
        room = g.get("room")

        if not message or not room:
            emit("error", {"message": "Invalid message"})
            return

        payload = {
            "sender_id": g.client_id,
            "sender_type": g.client_type,
            "sender_name": g.username,
            "message": message,
            "room": room,
            "ts": datetime.utcnow().isoformat() + "Z"
        }

        redis.rpush(
            f"chat:private:{room}",
            json.dumps(payload)
        )

        emit("receive_private_message", payload, room=room)

