from sqlalchemy.ext.declarative import declarative_base
from flask_socketio import SocketIO
import redis
from minio import Minio
from typing import Optional
from flask import Flask
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from contextlib import contextmanager
from authlib.integrations.flask_client import OAuth
from flask_socketio import SocketIO

"""create uninitialized extension objects to avoid circular imports"""
Base = declarative_base()
engine = None
SessionLocal = None
socketio = SocketIO(async_mode="eventlet", cors_allowed_origins="*")  
r = None
oauth = OAuth()

def init_db(app: Flask):
    """Initialize SQLAlchemy engine & sessionmaker"""
    global engine, SessionLocal
    DATABASE_URL = app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///./test.db")
    engine = create_engine(DATABASE_URL, echo=True, future=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    from app.Database.user_models import User
    from app.Database.vendors_model import Vendor
    from app.Database.profile_merchant import Profile_Merchant
    from app.Database.food_item import FoodItem
    from app.Database.order_single import OrderSingle
    from app.Database.order_multiple import OrderMultiple
    from app.Database.vendor_recieve_pay import Vendor_Payment
    from app.Database.api_payment import Payment_api_database
    from app.Database.order_single import OrderSingle
    from app.Database.order_multiple import OrderMultiple

    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal

""" resources that require app config — created in init_... functions"""
redis_client: Optional[redis.Redis] = None
minio_client: Optional[Minio] = None

def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db(app) first.")
    return SessionLocal()

def init_redis(app: Flask):
    global r
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url, decode_responses=True)
    return r


@contextmanager
def session_scope():
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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

def emit_to_room(room: str, event: str, data: dict):
    """
    Emit a Socket.IO event to a specific room.
    Uses the globally initialized socketio instance.
    """
    socketio.emit(
        event,
        data,
        room=room,
    )
 
