from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import Base


from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

class RiderAndStrawler(Base):
    __tablename__ = "riders_and_strawlers"

    id = Column(Integer, primary_key=True)

    # Link to users table
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Identity (Nigeria)
    nin = Column(String(11), nullable=False, unique=True)
    phone = Column(String(20), nullable=False, index=True)
    address = Column(String(255), nullable=False)
    identification_number = Column(String(50), nullable=False)

    # Status
    status = Column(String(32), default="inactive")  # inactive, active, busy, offline
    is_available = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    # Performance
    completed_rides = Column(Integer, default=0, nullable=False)

    # Travel
    destination = Column(String(255), nullable=True)
    anywhere = Column(String(255), nullable=True)

    # Bank details (for payouts)
    bank_name = Column(String(100), nullable=False)
    bank_code = Column(String(10), nullable=False)
    account_name = Column(String(150), nullable=False)
    account_number = Column(String(20), nullable=False)

    # Paystack virtual account / customer
    paystack_customer_code = Column(String(50), nullable=True)
    paystack_virtual_account = Column(String(20), nullable=True)

    # Timestamps
    last_update = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_rider_bank", "bank_code", "account_number"),
    )



    # ---------- Password helpers ----------
    def set_password(self, password: str):
        """Hash and set the rider password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the rider password"""
        return check_password_hash(self.password_hash, password)

    # ---------- Dictionary representation ----------
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "nin": self.nin,
            "status": self.status,
            "is_available": self.is_available,
            "completed_rides": self.completed_rides,
            "bank_name": self.bank_name,
            "account_name": self.account_name,
            "account_number": self.account_number,
            "last_update": (
                self.last_update.strftime("%Y-%m-%d %H:%M:%S")
                if self.last_update else None
            ),
        }

