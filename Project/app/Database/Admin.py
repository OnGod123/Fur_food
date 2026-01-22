from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, UniqueConstraint
from database import Base

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    paystack_customer_code = Column(String)
    paystack_virtual_account = Column(String)
    bank_code = Column(String)
    account_number = Column(String)
    account_name = Column(String)
    __table_args__ = (
        UniqueConstraint('username', name='uq_admin_username'),
        UniqueConstraint('email', name='uq_admin_email'),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



