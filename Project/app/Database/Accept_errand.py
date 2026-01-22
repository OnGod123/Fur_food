
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



class ErrandAcceptance(Base):
    __tablename__ = "accept_errands"

    id = Column(Integer, primary_key=True, autoincrement=True)

    errand_id = Column(Integer, nullable=False, unique=True)

    rider_id = Column(
        Integer, ForeignKey("rider_and_strawler.id"), nullable=False
    )

    rider_phone = Column(String(20), nullable=False)

    accepted_at = Column(DateTime, default=datetime.utcnow)

