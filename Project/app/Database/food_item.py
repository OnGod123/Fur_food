"""
Defines the FoodItem model for vendor menu items.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.extensions import Base
from app.Database.profile_merchant import Profile_Merchant

class FoodItem(Base):
    """
    Represents a menu item offered by a vendor.
    """

    __tablename__ = "food_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)

    product_name = Column(String(255), nullable=False)
    vendor_name = Column(String(255), nullable=False)
    description = Column(String(512), nullable=True)
    item_name = Column(String(255), nullable=False)
    item_description = Column(String(512), nullable=False)
    price = Column(Float, nullable=False)
    image_url = Column(String(512), nullable=True)

    available_from = Column(Time, nullable=True)
    available_to = Column(Time, nullable=True)
    is_available = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    
    vendor = relationship("Vendor", back_populates="menu_items")
    merchant = relationship("Profile_Merchant")

    def to_dict(self):
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "merchant_id": self.merchant_id,
            "product_name": self.product_name,
            "vendor_name": self.vendor_name,
            "description": self.description,
            "price": self.price,
            "image_url": self.image_url,
            "available_from": self.available_from.strftime("%H:%M") if self.available_from else None,
            "available_to": self.available_to.strftime("%H:%M") if self.available_to else None,
            "is_available": self.is_available,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
