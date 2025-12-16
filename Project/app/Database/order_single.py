"""
Defines the OrderSingle model for single-vendor user orders.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON, Float, String
from sqlalchemy.orm import relationship
from app.extensions import Base


class OrderSingle(Base):
    """
    Represents a single vendor order made by a user.
    """

    __tablename__ = "order_single"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_data = Column(JSON, nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor_name = Column(String(255), nullable=False)
    product_name = Column(String(255), nullable=False)
    recipient_address = Column(String(255), nullable=False)
    is_paid = Column(Boolean, default=False, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates = "orders")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_data": self.item_data,
            "total": self.total,
            "vendor_name": self.vendor_name,
            "product_name": self.product_name,
            "recipient_address": self.recipient_address,
            "created_at": self.created_at.isoformat(),
        }
