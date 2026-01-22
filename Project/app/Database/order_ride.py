from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.extensions import Base


class Ride_Order(Base):
    __tablename__ = "ride_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_phone = Column(String(20), nullable=False)

    pickup_location = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)

    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    accepted_ride = relationship("AcceptRide", backref="ride", uselist=False)

