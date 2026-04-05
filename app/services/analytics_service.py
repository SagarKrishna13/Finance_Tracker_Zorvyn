"""
Analytics service - all financial summary and insight computations.

Every calculation is done with SQL aggregate queries so the DB does the
heavy lifting. We never pull raw rows into memory just to count or sum them.

Summaries available:
  - Overall summary  : total income, expenses, net balance, transaction count
  - Category breakdown: per-category totals and percentage share
  - Monthly totals   : income vs expenses for the last 6 months
  - Trend            : this month vs last month spending delta
  - Recent activity  : last 10 transactions with a running balance
"""

from collections import defaultdict
from datetime import date, datetime
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Internal scope helper (mirrors transaction_service)
# ---------------------------------------------------------------------------

def _scoped_query(db: Session, current_user: User):
    q = db.query(Transaction)
    if current_user.role != UserRole.admin:
        q = q.filter(Transaction.user_id == current_user.id)
    return q


# ---------------------------------------------------------------------------
# 1. Overall summary
# ---------------------------------------------------------------------------

def get_summary(db: Session, current_user: User) -> dict:
    """
    Return total income, total expenses, net balance, and transaction count.
    """
    base = _scoped_query(db, current_user)

    income_row = (
        base.filter(Transaction.type == TransactionType.income)
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0.0))
        .scalar()
    )
    expense_row = (
        base.filter(Transaction.type == TransactionType.expense)
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0.0))
        .scalar()
    )
    total_count = base.count()

    total_income = round(float(income_row), 2)
    total_expenses = round(float(expense_row), 2)

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_balance": round(total_income - total_expenses, 2),
        "transaction_count": total_count,
    }


# ---------------------------------------------------------------------------
# 2. Category breakdown
# ---------------------------------------------------------------------------

def get_category_breakdown(db: Session, current_user: User) -> dict:
    """
    Return per-category totals for income and expenses, with percentage share.
    Percentages are calculated relative to total income / total expenses
    independently, so all income percentages add to 100 and all expense
    percentages add to 100.
    """
    rows = (
        _scoped_query(db, current_user)
        .with_entities(
            Transaction.type,
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .group_by(Transaction.type, Transaction.category)
        .all()
    )

    income_total = sum(r.total for r in rows if r.type == TransactionType.income)
    expense_total = sum(r.total for r in rows if r.type == TransactionType.expense)

    income_breakdown = []
    expense_breakdown = []

    for row in rows:
        entry = {
            "category": row.category.value,
            "total": round(float(row.total), 2),
            "count": row.count,
            "percentage": 0.0,
        }
        if row.type == TransactionType.income:
            entry["percentage"] = (
                round(float(row.total) / income_total * 100, 1) if income_total else 0.0
            )
            income_breakdown.append(entry)
        else:
            entry["percentage"] = (
                round(float(row.total) / expense_total * 100, 1) if expense_total else 0.0
            )
            expense_breakdown.append(entry)

    # Sort by total descending so the biggest categories come first
    income_breakdown.sort(key=lambda x: x["total"], reverse=True)
    expense_breakdown.sort(key=lambda x: x["total"], reverse=True)

    return {"income": income_breakdown, "expenses": expense_breakdown}


# ---------------------------------------------------------------------------
# 3. Monthly totals - last 6 months
# ---------------------------------------------------------------------------

def get_monthly_totals(db: Session, current_user: User) -> list[dict]:
    """
    Return month-by-month income and expense totals for the last 6 months.
    Months with no transactions are included with zero values so the
    frontend can always render a complete 6-bar chart.
    """
    rows = (
        _scoped_query(db, current_user)
        .with_entities(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        )
        .group_by("month", Transaction.type)
        .order_by("month")
        .all()
    )

    # Aggregate into a dict keyed by "YYYY-MM"
    monthly: dict[str, dict] = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    for row in rows:
        if row.type == TransactionType.income:
            monthly[row.month]["income"] = round(float(row.total), 2)
        else:
            monthly[row.month]["expenses"] = round(float(row.total), 2)

    # Build last-6-months labels regardless of whether data exists
    today = date.today()
    result = []
    for offset in range(5, -1, -1):
        # Go back `offset` months from today
        month_num = today.month - offset
        year = today.year
        while month_num <= 0:
            month_num += 12
            year -= 1
        label = f"{year}-{month_num:02d}"
        entry = monthly.get(label, {"income": 0.0, "expenses": 0.0})
        result.append(
            {
                "month": label,
                "income": entry["income"],
                "expenses": entry["expenses"],
                "net": round(entry["income"] - entry["expenses"], 2),
            }
        )

    return result


# ---------------------------------------------------------------------------
# 4. Spending trend - this month vs last month
# ---------------------------------------------------------------------------

def get_spending_trend(db: Session, current_user: User) -> dict:
    """
    Compare this month's expenses against last month's.
    Returns the delta amount and direction (up / down / flat).
    """
    today = date.today()

    def month_expense(year: int, month: int) -> float:
        first = date(year, month, 1)
        # Last day of month
        if month == 12:
            last = date(year + 1, 1, 1)
        else:
            last = date(year, month + 1, 1)
        total = (
            _scoped_query(db, current_user)
            .filter(
                Transaction.type == TransactionType.expense,
                Transaction.date >= first,
                Transaction.date < last,
            )
            .with_entities(func.coalesce(func.sum(Transaction.amount), 0.0))
            .scalar()
        )
        return round(float(total), 2)

    this_month = month_expense(today.year, today.month)
    prev_month_num = today.month - 1 if today.month > 1 else 12
    prev_year = today.year if today.month > 1 else today.year - 1
    last_month = month_expense(prev_year, prev_month_num)

    delta = round(this_month - last_month, 2)
    if delta > 0:
        direction = "up"
    elif delta < 0:
        direction = "down"
    else:
        direction = "flat"

    return {
        "this_month_expenses": this_month,
        "last_month_expenses": last_month,
        "delta": abs(delta),
        "direction": direction,
        "message": (
            f"Spending is {direction} by ₹{abs(delta):,.2f} compared to last month"
            if direction != "flat"
            else "Spending is the same as last month"
        ),
    }


# ---------------------------------------------------------------------------
# 5. Recent activity with running balance
# ---------------------------------------------------------------------------

def get_recent_activity(db: Session, current_user: User, limit: int = 10) -> dict:
    """
    Return the most recent `limit` transactions with a running balance.
    The running balance starts from the overall net and walks backward,
    giving the user a sense of how each transaction affected their balance.
    """
    summary = get_summary(db, current_user)
    net_balance = summary["net_balance"]

    recent = (
        _scoped_query(db, current_user)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(limit)
        .all()
    )

    activity = []
    running_balance = net_balance

    for t in recent:
        activity.append(
            {
                "id": t.id,
                "amount": t.amount,
                "type": t.type.value,
                "category": t.category.value,
                "date": str(t.date),
                "notes": t.notes,
                "balance_after": round(running_balance, 2),
            }
        )
        # Reverse the effect of this transaction to get the prior balance
        if t.type == TransactionType.income:
            running_balance -= t.amount
        else:
            running_balance += t.amount

    return {
        "current_balance": net_balance,
        "transactions": activity,
    }
