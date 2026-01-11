"""
Defines the Vendor model for restaurants/food vendors.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.extensions import Base
from app.Database.profile_merchant import Profile_Merchant
from app.Database.user_models import User
from app.Database.food_item import FoodItem

class Vendor(Base):
    """
    Represents a food vendor / merchant store.
    """

    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="vendor", uselist=False)

    business_name = Column(String(255), nullable=False, index=True)
    business_address = Column(String(255), nullable=False)
    business_email = Column(String(255), nullable=False, index=True)
    business_phone = Column(String(20), nullable=False, index=True)

    is_open = Column(Boolean, default=True)
    opening_time = Column(Time, nullable=True)
    closing_time = Column(Time, nullable=True)

    bank_name = Column(String(100), nullable=False)
    bank_code = Column(String(10), nullable=False)
    account_name = Column(String(150), nullable=False)
    account_number = Column(String(20), nullable=False)

    paystack_customer_code = Column(String(50), nullable=True)
    paystack_virtual_account = Column(String(20), nullable=True)

    is_verified = Column(Boolean, default=False)

    menu_items = relationship(
        "FoodItem",
        back_populates="vendor",
        cascade="all, delete-orphan"
    )

    merchants = relationship(
        "ProfileMerchant",
        back_populates="vendor",
        cascade="all, delete-orphan"
    )


    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_vendor_bank", "bank_code", "account_number"),
    )


    def to_dict(self, include_menu=False):
        data = {
            "id": self.id,
            "business_name": self.Business_name,
            "business_address": self.Business_address,
            "is_open": self.is_open,
            "opening_time": self.opening_time.strftime("%H:%M") if self.opening_time else None,
            "closing_time": self.closing_time.strftime("%H:%M") if self.closing_time else None,
            "bank_code": self.bank_code,
            "account_number": self.account_number,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        if include_menu:
            data["menu_items"] = [item.to_dict() for item in self.menu_items]

        return data

