
"""
Defines the Vendor_Payment model representing payments to vendors
for user orders.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.extensions import Base


class Vendor_Payment(Base):
    """
    Represents a payment made to a vendor.

    Attributes
    ----------
    user_id : int
        ID of the user making the payment.
    vendor_id : int
        ID of the vendor receiving the payment.
    order_id : int
        ID of the order associated with this payment.
    amount : float
        Total payment amount.
    fee : float
        Platform or processing fee (default: 700.0).
    vendor_amount : float
        Amount received by the vendor after fee deduction.
    payment_gateway : str
        Payment method, e.g., 'wallet'.
    status : str
        Payment status, e.g., 'pending', 'completed'.
    vendor_bank_code : str
        Vendor bank code (optional).
    vendor_account_number : str
        Vendor bank account number (optional).
    reference : str
        Unique reference identifier for the transaction.
    created_at : datetime
        Timestamp of payment creation.
    """

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("order_single.id"), nullable=False)

    amount = Column(Float, nullable=False)
    fee = Column(Float, default=700.0)
    vendor_amount = Column(Float, nullable=False)

    payment_gateway = Column(String(32), default="wallet")
    status = Column(String(32), default="pending")

    vendor_bank_code = Column(String(16))
    vendor_account_number = Column(String(32))

    reference = Column(String(64), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)


    user = relationship("User", backref="vendor_payments")
    vendor = relationship("Vendor", backref="payments")
    order = relationship("OrderSingle", backref="payment")

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "vendor_id": self.vendor_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "fee": self.fee,
            "vendor_amount": self.vendor_amount,
            "payment_gateway": self.payment_gateway,
            "status": self.status,
            "vendor_bank_code": self.vendor_bank_code,
            "vendor_account_number": self.vendor_account_number,
            "reference": self.reference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

