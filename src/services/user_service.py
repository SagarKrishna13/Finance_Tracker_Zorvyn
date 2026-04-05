"""
User service - all user-related business logic.

Rules enforced here (not in the router):
  - Email uniqueness
  - Password verification on login
  - Token generation
"""

from sqlalchemy.orm import Session

from src.core.security import hash_password, verify_password, create_access_token
from src.exceptions import ConflictError, UnauthorizedError
from src.models.user import User, UserRole
from src.schemas.user import UserRegisterRequest


def register_user(db: Session, payload: UserRegisterRequest) -> User:
    """
    Create a new user.
    Raises ConflictError if the email is already registered.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ConflictError(
            f"An account with the email '{payload.email}' already exists",
            field="email",
        )

    user = User(
        name=payload.name.strip(),
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> dict:
    """
    Verify credentials and return an access token + user record.
    Raises UnauthorizedError on any mismatch (intentionally vague to prevent
    email enumeration).
    """
    user = db.query(User).filter(User.email == email, User.is_active == True).first()

    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token, "token_type": "bearer", "user": user}


def get_all_users(db: Session) -> list[User]:
    """Return all users - admin only."""
    return db.query(User).order_by(User.created_at.desc()).all()
