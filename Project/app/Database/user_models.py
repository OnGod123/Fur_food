
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, JSON,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.extensions import Base
from app.Database.wallet import Wallet
from app.Database.order_single import  OrderSingle
from app.Database.multiple_order import OrderMultiple
from app.Database.profile_merchant import Profile_Merchant

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)

    email = Column(String(320), nullable=True, index=True)
    phone = Column(String(32), nullable=True, index=True)
    password_hash = Column(String(256), nullable=True)
    name = Column(String(120), nullable=True)

    google_id = Column(String(256), nullable=True, index=True)
    facebook_id = Column(String(256), nullable=True, index=True)

    last_ip = Column(String(45), nullable=True)
    is_guest = Column(Boolean, nullable=False, default=False)

    extra_data = Column(JSON, nullable=True, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email", sqlite_on_conflict="IGNORE"),
        UniqueConstraint("phone", name="uq_users_phone", sqlite_on_conflict="IGNORE"),
        UniqueConstraint("google_id", name="uq_users_google_id", sqlite_on_conflict="IGNORE"),
        UniqueConstraint("facebook_id", name="uq_users_facebook_id", sqlite_on_conflict="IGNORE"),
    )

    wallet = relationship(
        "Wallet",
        back_populates="user",
        uselist=False,
    )

    vendors = relationship(
        "Vendor",
        back_populates="user",
    )

    orders = relationship(
        "OrderSingle",
        back_populates="user",
    )

    multiple_orders = relationship(
        "OrderMultiple",
        back_populates="user",
        lazy="dynamic",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "phone": self.phone,
            "name": self.name,
            "google_id": self.google_id,
            "facebook_id": self.facebook_id,
            "is_guest": self.is_guest,
            "last_ip": self.last_ip,
            "extra_data": self.extra_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
