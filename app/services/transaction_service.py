"""
Transaction service - all transaction business logic.

Key design decisions:
  - Admins see ALL transactions; non-admins see only their own.
  - Pagination is always applied to list queries - never return unbounded sets.
  - Search targets both `notes` and `category` via case-insensitive LIKE.
  - Export bypasses pagination but applies all the same filters.
  - CSV export uses the stdlib `csv` module - no extra dependencies.
"""

import csv
import io
import json
from datetime import date
from math import ceil
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.models.user import User, UserRole
from app.schemas.transaction import TransactionCreateRequest, TransactionUpdateRequest


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _base_query(db: Session, current_user: User):
    """
    Start a query scoped to the correct set of transactions.
    Admins see everything; users see only their own records.
    """
    q = db.query(Transaction)
    if current_user.role != UserRole.admin:
        q = q.filter(Transaction.user_id == current_user.id)
    return q


def _apply_filters(
    query,
    transaction_type: Optional[TransactionType],
    category: Optional[TransactionCategory],
    from_date: Optional[date],
    to_date: Optional[date],
    search: Optional[str],
):
    """Apply all optional filters to an existing query and return it."""
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)

    if category:
        query = query.filter(Transaction.category == category)

    if from_date:
        query = query.filter(Transaction.date >= from_date)

    if to_date:
        query = query.filter(Transaction.date <= to_date)

    if search:
        term = f"%{search.strip()}%"
        # Search across notes AND category name
        query = query.filter(
            or_(
                Transaction.notes.ilike(term),
                Transaction.category.ilike(term),
            )
        )

    return query


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_transaction(
    db: Session, payload: TransactionCreateRequest, current_user: User
) -> Transaction:
    transaction = Transaction(
        user_id=current_user.id,
        amount=payload.amount,
        type=payload.type,
        category=payload.category,
        date=payload.date,
        notes=payload.notes,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_transaction_by_id(
    db: Session, transaction_id: int, current_user: User
) -> Transaction:
    """
    Return a single transaction.
    Non-admins can only see their own records.
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise NotFoundError(f"Transaction with ID {transaction_id} does not exist")

    if current_user.role != UserRole.admin and transaction.user_id != current_user.id:
        # Do not reveal that the record exists - return the same 404
        raise NotFoundError(f"Transaction with ID {transaction_id} does not exist")

    return transaction


def update_transaction(
    db: Session,
    transaction_id: int,
    payload: TransactionUpdateRequest,
    current_user: User,
) -> Transaction:
    transaction = get_transaction_by_id(db, transaction_id, current_user)

    # Apply only the fields that were actually provided
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)
    return transaction


def delete_transaction(
    db: Session, transaction_id: int, current_user: User
) -> None:
    transaction = get_transaction_by_id(db, transaction_id, current_user)
    db.delete(transaction)
    db.commit()


# ---------------------------------------------------------------------------
# Paginated list with filters + search
# ---------------------------------------------------------------------------

def list_transactions(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 10,
    transaction_type: Optional[TransactionType] = None,
    category: Optional[TransactionCategory] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
) -> dict:
    """
    Return a paginated, filtered, optionally searched list of transactions.

    Pagination metadata included in the response makes it trivial for a
    frontend to render page controls without any additional requests.
    """
    if from_date and to_date and from_date > to_date:
        raise BadRequestError(
            "from_date cannot be later than to_date", field="from_date"
        )

    query = _base_query(db, current_user)
    query = _apply_filters(query, transaction_type, category, from_date, to_date, search)

    total = query.count()
    total_pages = ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size

    transactions = (
        query.order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "data": transactions,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


# ---------------------------------------------------------------------------
# Export - CSV and JSON (no pagination, same filters applied)
# ---------------------------------------------------------------------------

def export_transactions(
    db: Session,
    current_user: User,
    export_format: str,
    transaction_type: Optional[TransactionType] = None,
    category: Optional[TransactionCategory] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
) -> tuple[str, str]:
    """
    Export all matching transactions as CSV or JSON.

    Returns a (content_string, media_type) tuple so the router can
    build the appropriate StreamingResponse without knowing about
    serialization details.
    """
    if export_format not in ("csv", "json"):
        raise BadRequestError(
            "Invalid export format. Allowed values: csv, json", field="format"
        )

    if from_date and to_date and from_date > to_date:
        raise BadRequestError(
            "from_date cannot be later than to_date", field="from_date"
        )

    query = _base_query(db, current_user)
    query = _apply_filters(query, transaction_type, category, from_date, to_date, search)
    transactions = query.order_by(Transaction.date.desc()).all()

    if export_format == "csv":
        return _serialize_csv(transactions), "text/csv"
    else:
        return _serialize_json(transactions), "application/json"


def _serialize_csv(transactions: list[Transaction]) -> str:
    """Convert a list of Transaction ORM objects to a CSV string."""
    output = io.StringIO()
    fieldnames = ["id", "user_id", "amount", "type", "category", "date", "notes", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for t in transactions:
        writer.writerow(
            {
                "id": t.id,
                "user_id": t.user_id,
                "amount": t.amount,
                "type": t.type.value,
                "category": t.category.value,
                "date": str(t.date),
                "notes": t.notes or "",
                "created_at": str(t.created_at)[:19],
            }
        )

    output.seek(0)
    return output.getvalue()


def _serialize_json(transactions: list[Transaction]) -> str:
    """Convert a list of Transaction ORM objects to a JSON string."""
    records = [
        {
            "id": t.id,
            "user_id": t.user_id,
            "amount": t.amount,
            "type": t.type.value,
            "category": t.category.value,
            "date": str(t.date),
            "notes": t.notes,
            "created_at": str(t.created_at)[:19],
        }
        for t in transactions
    ]
    return json.dumps({"success": True, "total": len(records), "data": records}, indent=2)
