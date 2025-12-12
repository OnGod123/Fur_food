"""
user_models.py

Defines the User ORM model. This model represents a platform user including
standard account fields, OAuth IDs, metadata, and relationships to wallets,
orders, and vendors.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, JSON,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.extensions import Base


class User(Base):
    """
    Represents an application user, including authentication info,
    contact details, and metadata.

    Attributes
    ----------
    id : int
        Primary key.
    email : str | None
        Optional email address. Expected: valid email or None.
    phone : str | None
        Optional phone number in E.164 or local format.
    password_hash : str | None
        Hashed password. Null for OAuth-only or guest accounts.
    name : str | None
        Display name.

    google_id : str | None
        Google OAuth ID. Unique.
    facebook_id : str | None
        Facebook OAuth ID. Unique.

    last_ip : str | None
        Last IP address seen. Useful for logging & fraud checks.

    is_guest : bool
        True for automatically generated guest accounts.

    extra_data : dict
        Arbitrary JSON metadata such as:
        - email_verified: bool
        - phone_verified: bool
        - referral_code: str
        - device_info: dict

    created_at : datetime
        Row creation timestamp.
    updated_at : datetime
        Last update timestamp.

    Relationships
    -------------
    wallets : Wallet
        One-to-one relationship with user wallet.
    vendors : list[Vendor]
        Vendor accounts owned by user.
    orders : list[OrderSingle]
        All single orders placed by the user.
    multiple_orders : list[OrderMultiple]
        Multiple-order batches placed by the user.
    """

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
        nullable=False
    )

    __table_args__ = (
        
        UniqueConstraint("email", name="uq_users_email", sqlite_on_conflict="IGNORE"),
        UniqueConstraint("phone", name="uq_users_phone", sqlite_on_conflict="IGNORE"),
        UniqueConstraint("google_id", name="uq_users_google_id", sqlite_on_conflict="IGNORE"),
        UniqueConstraint("facebook_id", name="uq_users_facebook_id", sqlite_on_conflict="IGNORE"),
    )

    
    wallets = relationship("Wallet", backref="user", uselist=False)
    vendors = relationship("Vendor", backref="user", lazy=True)
    orders = relationship("OrderSingle", backref="user", lazy=True)
    multiple_orders = relationship("OrderMultiple", back_populates="user", lazy="dynamic")

    def to_dict(self) -> dict:
        """Convert the User model into a serializable dictionary."""
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