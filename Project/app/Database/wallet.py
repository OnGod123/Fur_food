"""
Defines Wallet ORM model.
Handles user wallet balances using integer currency units.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.extensions import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    balance = Column(Integer, default=0, nullable=False)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = relationship("User", back_populates="wallet")

    # -------------------------------
    # DB-LEVEL OPERATIONS ONLY
    # -------------------------------

    @staticmethod

    def debit(session, user_id: int, amount: int) -> int:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        wallet = (
            session.query(Wallet)
            .filter_by(user_id=user_id)
            .with_for_update()
            .first()
        )

        if not wallet:
            raise ValueError("Wallet not found")

        if wallet.balance < amount:
            raise ValueError("Insufficient wallet balance")

        wallet.balance -= amount


    
    return wallet.balance


    @staticmethod

    def credit(session, user_id: int, amount: int) -> int:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        wallet = (
            session.query(Wallet)
            .filter_by(user_id=user_id)
            .with_for_update()
            .first()
        )

        if not wallet:
            raise ValueError("Wallet not found")

        wallet.balance += amount
        return wallet.balance


