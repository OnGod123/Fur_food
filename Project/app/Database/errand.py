
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


class Errand(Base):
    __tablename__ = "errands"

    # ---------------- Primary ----------------
    id = Column(Integer, primary_key=True)

    # ---------------- Ownership ----------------
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Optional: only filled when persisted (not Redis lock)
    rider_id = Column(
        Integer,
        ForeignKey("riders_and_strawlers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # ---------------- Errand Info ----------------
    description = Column(String(255), nullable=False)

    pickup_address = Column(String(255), nullable=False)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)

    destination_address = Column(String(255), nullable=False)

    # ---------------- Status ----------------
    # pending | accepted | in_progress | completed | cancelled
    status = Column(String(32), nullable=False, default="pending", index=True)

    # ---------------- Timestamps ----------------
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # ---------------- Relationships ----------------
    user = relationship("User", backref="errands")
    rider = relationship("RiderAndStrawler", backref="errands")

    # ---------------- Indexes ----------------
    __table_args__ = (
        Index("idx_errand_status_created", "status", "created_at"),
    )

    # ---------------- Helpers ----------------
    def mark_accepted(self, rider_id: int):
        self.status = "accepted"
        self.rider_id = rider_id
        self.accepted_at = datetime.utcnow()

    def mark_pending(self):
        self.status = "pending"
        self.rider_id = None
        self.accepted_at = None

    def mark_completed(self):
        self.status = "completed"
        self.completed_at = datetime.utcnow()

    def mark_cancelled(self):
        self.status = "cancelled"
        self.cancelled_at = datetime.utcnow()

