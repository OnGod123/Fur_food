from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.extensions import Base


class Payment_api_database(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True)
    provider = Column(String(64), nullable=False)
    provider_txn_id = Column(String(128), index=True)
    tx_ref = Column(String(128), unique=True, index=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="NGN")
    direction = Column(String(16), nullable=False)

    target_user_id = Column(Integer, ForeignKey("users.id"))
    meta = Column(JSON)

    verified_payment = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)

    user = relationship("User")

