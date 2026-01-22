
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index
)
from sqlalchemy.orm import relationship
from app.extensions import Base



class RideAcceptance(Base):
    __tablename__ = "accept_rides"

    id = Column(Integer, primary_key=True, autoincrement=True)

    ride_order_id = Column(
        Integer, ForeignKey("ride_orders.id"), unique=True, nullable=False
    )

    rider_id = Column(
        Integer, ForeignKey("rider_and_strawler.id"), nullable=False
    )

    rider_phone = Column(String(20), nullable=False)

    accepted_at = Column(DateTime, default=datetime.utcnow)

