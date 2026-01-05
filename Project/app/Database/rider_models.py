from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Index
)
from sqlalchemy.orm import relationship
from app.extensions import Base


class RiderAndStrawler(Base):
    __tablename__ = "riders"

    id = Column(Integer, primary_key=True)

    # 🔗 Link to main user table
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", backref="rider_profile", lazy="joined")

    # 🔐 Authentication
    password_hash = Column(String(255), nullable=True)

    # 📞 Contact
    phone = Column(String(20), nullable=False, index=True)

    # 🏦 Bank Verification (Paystack resolve)
    bank_code = Column(String(10), nullable=False)
    account_number = Column(String(20), nullable=False)
    account_name = Column(String(150), nullable=False)

    # 🚦 Rider State
    status = Column(String(20), default="inactive")   # inactive | active | suspended
    is_available = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    Destination_travel = Column(String(255), nullable=True)

    # ⏱️ Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_rider_bank", "bank_code", "account_number"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "phone": self.phone,
            "bank_code": self.bank_code,
            "account_number": self.account_number,
            "account_name": self.account_name,
            "status": self.status,
            "is_available": self.is_available,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
            "last_update": self.last_update.isoformat(),
        }

