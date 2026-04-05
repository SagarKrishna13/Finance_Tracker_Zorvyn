"""
Transactions router.

Endpoints:
  GET    /transactions          - paginated list with filters + search  (user+)
  POST   /transactions          - create a transaction                  (user+)
  GET    /transactions/{id}     - single transaction                    (user+)
  PUT    /transactions/{id}     - update a transaction                  (admin)
  DELETE /transactions/{id}     - delete a transaction                  (admin)
  GET    /transactions/export   - export as CSV or JSON                 (user+)

Role logic:
  - Users see only their own transactions.
  - Admins see all transactions across all users.
  - Only admins can update or delete.
  - Both users and admins can create, read, and export.
"""

import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import require_role, get_public_user
from app.models.transaction import TransactionType, TransactionCategory
from app.models.user import User
from app.schemas.common import SuccessResponse, PaginatedResponse
from app.schemas.transaction import (
    TransactionCreateRequest,
    TransactionUpdateRequest,
    TransactionResponse,
)
from app.services import transaction_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Export - must be defined BEFORE /{id} routes to avoid path conflicts
# ---------------------------------------------------------------------------

@router.get(
    "/export",
    summary="Export transactions as CSV or JSON (analyst+)",
    responses={
        200: {
            "description": "File download - CSV or JSON",
            "content": {"text/csv": {}, "application/json": {}},
        }
    },
)
def export_transactions(
    format: str = Query("csv", pattern="^(csv|json)$", description="Export format: csv or json"),
    type: Optional[TransactionType] = Query(None, description="Filter by type"),
    category: Optional[TransactionCategory] = Query(None, description="Filter by category"),
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search in notes and category"),
    current_user: User = Depends(get_public_user),
    db: Session = Depends(get_db),
):
    content, media_type = transaction_service.export_transactions(
        db=db,
        current_user=current_user,
        export_format=format,
        transaction_type=type,
        category=category,
        from_date=from_date,
        to_date=to_date,
        search=search,
    )

    filename = f"transactions.{format}"
    return StreamingResponse(
        io.StringIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# List (paginated + filtered + searchable)
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=PaginatedResponse[TransactionResponse],
    summary="List transactions with pagination, filters, and search (user+)",
)
def list_transactions(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(
        settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description=f"Results per page (max {settings.MAX_PAGE_SIZE})",
    ),
    type: Optional[TransactionType] = Query(None, description="Filter by income or expense"),
    category: Optional[TransactionCategory] = Query(None, description="Filter by category"),
    from_date: Optional[date] = Query(None, description="Filter from this date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter up to this date (YYYY-MM-DD)"),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=100,
        description="Search keyword matched against notes and category",
    ),
    current_user: User = Depends(get_public_user),
    db: Session = Depends(get_db),
):
    result = transaction_service.list_transactions(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        transaction_type=type,
        category=category,
        from_date=from_date,
        to_date=to_date,
        search=search,
    )
    return {"success": True, **result}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=SuccessResponse[TransactionResponse],
    status_code=201,
    summary="Create a transaction (user+)",
)
def create_transaction(
    payload: TransactionCreateRequest,
    current_user: User = Depends(get_public_user),
    db: Session = Depends(get_db),
):
    transaction = transaction_service.create_transaction(db, payload, current_user)
    return {
        "success": True,
        "data": transaction,
        "message": "Transaction created successfully",
    }


# ---------------------------------------------------------------------------
# Single record
# ---------------------------------------------------------------------------

@router.get(
    "/{transaction_id}",
    response_model=SuccessResponse[TransactionResponse],
    summary="Get a single transaction by ID (user+)",
)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_public_user),
    db: Session = Depends(get_db),
):
    transaction = transaction_service.get_transaction_by_id(db, transaction_id, current_user)
    return {"success": True, "data": transaction}


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.put(
    "/{transaction_id}",
    response_model=SuccessResponse[TransactionResponse],
    summary="Update a transaction (admin only)",
)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdateRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    transaction = transaction_service.update_transaction(db, transaction_id, payload, current_user)
    return {
        "success": True,
        "data": transaction,
        "message": "Transaction updated successfully",
    }


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{transaction_id}",
    status_code=204,
    summary="Delete a transaction (admin only)",
)
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    transaction_service.delete_transaction(db, transaction_id, current_user)
    # 204 No Content - no response body
