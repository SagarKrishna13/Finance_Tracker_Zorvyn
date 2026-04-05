"""
Transaction request and response schemas.

Field-level rules enforced by Pydantic (shape / type / range).
Cross-field and DB-dependent rules are enforced in transaction_service.py.
"""

from typing import Optional
from datetime import date
from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from src.models.transaction import TransactionType, TransactionCategory


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class TransactionCreateRequest(BaseModel):
    amount: float
    type: TransactionType
    category: TransactionCategory
    date: date
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2)

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Transaction date cannot be in the future")
        return v

    @field_validator("notes")
    @classmethod
    def notes_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 500:
            raise ValueError("Notes cannot exceed 500 characters")
        return v


class TransactionUpdateRequest(BaseModel):
    """All fields optional - only provided fields will be updated (PATCH semantics)."""

    amount: Optional[float] = None
    type: Optional[TransactionType] = None
    category: Optional[TransactionCategory] = None
    date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2) if v is not None else v

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("Transaction date cannot be in the future")
        return v

    @model_validator(mode="after")
    def at_least_one_field(self) -> "TransactionUpdateRequest":
        if all(
            v is None
            for v in [self.amount, self.type, self.category, self.date, self.notes]
        ):
            raise ValueError("At least one field must be provided for an update")
        return self


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount: float
    type: TransactionType
    category: TransactionCategory
    date: date
    notes: Optional[str]
    created_at: str

    @field_validator("created_at", mode="before")
    @classmethod
    def format_datetime(cls, v) -> str:
        return str(v)[:19]  # "YYYY-MM-DD HH:MM:SS"
