"""
Transaction ORM model.

Each record captures a single financial event - either income or an expense.
The `notes` field is the primary search target for full-text keyword search.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Date,
    DateTime, Enum, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from src.core.database import Base


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


# Predefined categories - kept as an enum so the DB stays consistent.
# The router accepts only these values; custom categories can be added here.
class TransactionCategory(str, enum.Enum):
    salary = "salary"
    freelance = "freelance"
    investment = "investment"
    food = "food"
    rent = "rent"
    transport = "transport"
    utilities = "utilities"
    healthcare = "healthcare"
    entertainment = "entertainment"
    education = "education"
    shopping = "shopping"
    other = "other"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    category = Column(Enum(TransactionCategory), nullable=False)
    date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Back-reference to the owning user
    owner = relationship("User", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.type} amount={self.amount}>"
