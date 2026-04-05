"""
Seed script - populates the database with default users and empty histories.

Creates two users:
  admin@demo.com / Admin1234 (role: admin)
  user@demo.com  / User1234  (role: user)
"""

import sys
import os

# Make sure the project root is on the path when running directly
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
import random

from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.transaction import Transaction, TransactionType, TransactionCategory


def run():
    # Force fresh tables (handled by main.py usually, but good for direct CLI use)
    from app.models import user, transaction  # noqa: F401
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # ------------------------------------------------------------------
        # 1. Users
        # ------------------------------------------------------------------
        if db.query(User).count() == 0:
            admin = User(
                name="System Admin",
                email="admin@demo.com",
                hashed_password=hash_password("Admin1234"),
                role=UserRole.admin,
            )
            standard_user = User(
                name="Standard User",
                email="user@demo.com",
                hashed_password=hash_password("User1234"),
                role=UserRole.user,
            )
            db.add_all([admin, standard_user])
            db.commit()
            print("Users seeded: admin@demo.com, user@demo.com")
        
        user_account = db.query(User).filter(User.email == "user@demo.com").first()

        # ------------------------------------------------------------------
        # 2. Transactions (Last 6 Months)
        # ------------------------------------------------------------------
        # Clear existing transactions to avoid duplicates on re-seed
        db.query(Transaction).delete()
        db.commit()

        print("Generating 6 months of realistic data for 'Standard User'...")

        start_date = date.today() - timedelta(days=180)
        current_date = start_date
        
        while current_date <= date.today():
            
            # --- Monthly Income (Salary on the 1st) ---
            if current_date.day == 1:
                salary = Transaction(
                    user_id=user_account.id,
                    amount=55000.0,
                    type=TransactionType.income,
                    category=TransactionCategory.salary,
                    date=current_date,
                    notes=f"Monthly Salary - {current_date.strftime('%B %Y')}"
                )
                db.add(salary)
                
                # Monthly Rent (Rent on the 1st)
                rent = Transaction(
                    user_id=user_account.id,
                    amount=15000.0,
                    type=TransactionType.expense,
                    category=TransactionCategory.rent,
                    date=current_date,
                    notes=f"Apartment Rent - {current_date.strftime('%B %Y')}"
                )
                db.add(rent)

            # --- Occasional Freelance Income (Random days) ---
            if random.random() < 0.05: # 5% chance daily
                db.add(Transaction(
                    user_id=user_account.id,
                    amount=round(random.uniform(2000, 8000), 2),
                    type=TransactionType.income,
                    category=TransactionCategory.freelance,
                    date=current_date,
                    notes="Client Project Payout"
                ))

            # --- Fixed Utilities (Around the 10th) ---
            if current_date.day == 10:
                db.add(Transaction(
                    user_id=user_account.id,
                    amount=round(random.uniform(2500, 4500), 2),
                    type=TransactionType.expense,
                    category=TransactionCategory.utilities,
                    date=current_date,
                    notes="Electricity & Water Bill"
                ))

            # --- Daily Food/Transport (Frequent) ---
            if random.random() < 0.6: # 60% chance daily
                db.add(Transaction(
                    user_id=user_account.id,
                    amount=round(random.uniform(200, 800), 2),
                    type=TransactionType.expense,
                    category=random.choice([TransactionCategory.food, TransactionCategory.transport]),
                    date=current_date,
                    notes=random.choice(["Office Lunch", "Grocery", "Quick Snacks", "Commute", "Uber Ride"])
                ))

            # --- Entertainment/Shopping (Weekends) ---
            if current_date.weekday() >= 5: # Sat/Sun
                if random.random() < 0.4:
                    db.add(Transaction(
                        user_id=user_account.id,
                        amount=round(random.uniform(1500, 6000), 2),
                        type=TransactionType.expense,
                        category=random.choice([TransactionCategory.entertainment, TransactionCategory.shopping]),
                        date=current_date,
                        notes=random.choice(["Movie Night", "New Clothes", "Dinner Out", "Weekend Trip"])
                    ))

            # --- Healthcare/Education (Rare) ---
            if random.random() < 0.01:
                db.add(Transaction(
                    user_id=user_account.id,
                    amount=round(random.uniform(2000, 10000), 2),
                    type=TransactionType.expense,
                    category=random.choice([TransactionCategory.healthcare, TransactionCategory.education]),
                    date=current_date,
                    notes="Miscellaneous health/study expense"
                ))

            current_date += timedelta(days=1)

        db.commit()
        print(f"Success: {db.query(Transaction).count()} transactions seeded.")
        print("-" * 55)

    finally:
        db.close()


if __name__ == "__main__":
    run()
