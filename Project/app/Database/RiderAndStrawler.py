from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import Base


class RiderAndStrawler(Base):
    __tablename__ = "riders_and_strawlers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Identity (Nigeria)
    nin = Column(String(11), nullable=False, unique=True)

    # Status
    status = Column(String(32), default="inactive")  # active, busy, offline
    is_available = Column(Boolean, default=True)

    # Performance
    completed_rides = Column(Integer, default=0, nullable=False)

    # Bank details
    bank_name = Column(String(100), nullable=False)
    account_name = Column(String(100), nullable=False)
    account_number = Column(String(20), nullable=False)
    address = Column(String(255), nullable=False)

    # Hashed password
    password_hash = Column(String(255), nullable=False)

    # Timestamps
    last_update = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
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

