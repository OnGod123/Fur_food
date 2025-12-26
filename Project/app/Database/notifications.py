"""
Defines Notification model for user notifications.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from app.extensions import Base

class Notification(Base):
    """
    Represents a notification sent to a user.
    """

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(String(64), nullable=False)
    type = Column(String(64), nullable=False)

    # FIXED vendor fields (typos, relationship syntax, ForeignKey)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    vendor = relationship("Vendor", backref="notifications")

    payload = Column(JSON, nullable=True) #order paylaod
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "type": self.type,
            "vendor_id": self.vendor_id,
            "payload": self.payload,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat()
            if self.created_at else None,
        }
