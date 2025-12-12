from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import redis
from minio import Minio
from typing import Optional
from flask import Flask


"""create uninitialized extension objects to avoid circular imports"""
db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*")  

""" resources that require app config — created in init_... functions"""
redis_client: Optional[redis.Redis] = None
minio_client: Optional[Minio] = None


def init_redis(app: Flask):
    """Initialize the redis_client using app config. Returns the client."""
    global redis_client
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    return redis_client


def init_minio(app: Flask):
    """Initialize the minio_client using app config. Returns the client."""
    global minio_client
    minio_client = Minio(
        app.config.get("MINIO_ENDPOINT", "localhost:9000"),
        access_key=app.config.get("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=app.config.get("MINIO_SECRET_KEY", "minioadmin"),
        secure=app.config.get("MINIO_SECURE", False),
    )
    return minio_client
 