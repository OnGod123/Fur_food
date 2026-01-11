"""
Defines Delivery model for order deliveries.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.extensions import Base

class Delivery(Base):
    """
    Represents a delivery for single or multiple orders.

    Attributes
    ----------
    user_id : int
        ID of the user who will receive the delivery.
    order_single_id : int | None
        ID of the associated single order.
    order_multiple_id : int | None
        ID of the associated multiple order.
    address : str
        Delivery address.
    delivery_fee : float | None
        Fee charged for delivery.
    status : str
        Status of the delivery (default: 'pending').
    created_at : datetime
        Timestamp when the delivery was created.
    """

    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_single_id = Column(Integer, ForeignKey("order_single.id"), nullable=True)
    order_multiple_id = Column(Integer, ForeignKey("order_multiple.id"), nullable=True)
    address = Column(String(255), nullable=False)
    delivery_fee = Column(Float, nullable=True)
    status = Column(String(50), default="pending")
    rider_id = Column(Integer, ForeignKey("RiderAndStrawler.id")
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", backref="deliveries")
    order_single = relationship("OrderSingle", backref="delivery", uselist=False)
    order_multiple = relationship("OrderMultiple", backref="delivery", uselist=False)
    delivery_address = Column(string(50), nullable = False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "order_single_id": self.order_single_id,
            "order_multiple_id": self.order_multiple_id,
            "address": self.address,
            "delivery_fee": self.delivery_fee,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
