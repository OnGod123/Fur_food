"""
Defines the OrderMultiple model for multi-vendor user orders.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON, Float, String, Boolean
from sqlalchemy.orm import relationship
from app.extensions import Base


class OrderMultiple(Base):
    """
    Represents an order that includes multiple vendors/items by a user.
    """

    __tablename__ = "order_multiple"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    items_data = Column(JSON, nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor_name = Column(String(255), nullable=False)
    product_name = Column(String(255), nullable=False)
    recipient_address = Column(String(255), nullable=False)
    is_paid = Column(Boolean, default=False, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates = "multiple_orders")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "items_data": self.items_data,
            "total": self.total,
            "vendor_name": self.vendor_name,
            "product_name": self.product_name,
            "recipient_address": self.recipient_address,
            "created_at": self.created_at.isoformat(),
        }
