"""
Analytics router.

Endpoints:
  GET /analytics/summary          - totals and net balance         (public)
  GET /analytics/category         - per-category breakdown         (public)
  GET /analytics/monthly          - last 6 months income/expense   (public)
  GET /analytics/trend            - this month vs last month spend (public)
  GET /analytics/recent           - recent activity + running bal  (public)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_public_user
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.services import analytics_service

router = APIRouter()


@router.get(
    "/summary",
    response_model=SuccessResponse[dict],
    summary="Overall financial summary (public)",
)
def summary(
    current_user: User = Depends(get_public_user),
    db: Session = Depends(get_db),
):
    data = analytics_service.get_summary(db, current_user)
    return {"success": True, "data": data}


@router.get(
    "/category",
    response_model=SuccessResponse[dict],
    summary="Income and expense breakdown by category (public)",
)
def category_breakdown(
    current_user: User = Depends(get_public_user),
    db: Session = Depends(get_db),
):
    data = analytics_service.get_category_breakdown(db, current_user)
    return {"success": True, "data": data}


@router.get(
    "/monthly",
    response_model=SuccessResponse[list],
    summary="Monthly income vs expenses for the last 6 months (public)",
)
def monthly_totals(
    current_user: User = Depends(get_public_user),
    db: Session = Depends(get_db),
):
    data = analytics_service.get_monthly_totals(db, current_user)
    return {"success": True, "data": data}


@router.get(
    "/trend",
    response_model=SuccessResponse[dict],
    summary="Spending trend - this month vs last month (public)",
)
def spending_trend(
    current_user: User = Depends(get_public_user),
    db: Session = Depends(get_db),
):
    data = analytics_service.get_spending_trend(db, current_user)
    return {"success": True, "data": data}


@router.get(
    "/recent",
    response_model=SuccessResponse[dict],
    summary="Recent transactions with running balance (public)",
)
def recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of recent transactions to return"),
    current_user: User = Depends(get_public_user),
    db: Session = Depends(get_db),
):
    data = analytics_service.get_recent_activity(db, current_user, limit=limit)
    return {"success": True, "data": data}
