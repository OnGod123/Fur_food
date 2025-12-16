from datetime import datetime
from sqlalchemy import Column, Integer, Boolean, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.extensions import Base

class Profile_Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)

    password_hash = Column(String(256), nullable=False)
    account_number = Column(String(64), nullable=True)
    order_tracker = Column(String(128), nullable=True, unique=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user  = relationship("User", backref="merchant_account", uselist=False)
    vendor  = relationship("Vendor", back_populates="merchants")

    

    __table_args__ = (
        UniqueConstraint("user_id", "vendor_id", name="uq_user_vendor"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor.name if self.vendor else None,
            "account_number": self.account_number,
            "order_tracker": self.order_tracker,
            "is_active": self.is_active,
        }
