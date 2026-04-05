"""
FastAPI dependencies for authentication and role-based access control.

Two dependency patterns:
  1. get_public_user      - returns the seeded public/default user if no token is provided.
                           Used by endpoints that should be accessible without login.
  2. require_role(roles)  - strict check; raises 401/403 if token is missing or wrong role.
                           Used by admin-only endpoints (update, delete).
"""

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from typing import Optional
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import decode_access_token
from src.exceptions import UnauthorizedError, ForbiddenError
from src.models.user import User, UserRole

# auto_error=False so missing token does not raise 401 automatically
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Public dependency - used by user-facing endpoints (no login required)
# ---------------------------------------------------------------------------

DEFAULT_USER_EMAIL = "user@demo.com"


def get_public_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    If a valid JWT is provided in the Authorization header, return the authenticated user.
    If no token (or an invalid one), return the seeded default 'user@demo.com' account.
    This bypasses OAuth2PasswordBearer to avoid any automatic 'Not authenticated' errors.
    """
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    if token:
        try:
            payload = decode_access_token(token)
            user_id: Optional[int] = payload.get("sub")
            if user_id:
                user = db.query(User).filter(
                    User.id == int(user_id), User.is_active == True
                ).first()
                if user:
                    return user
        except JWTError:
            pass  # fall through to default user

    # No token or invalid token - return the public default user
    default_user = db.query(User).filter(User.email == DEFAULT_USER_EMAIL).first()
    if not default_user:
        raise UnauthorizedError("Default user account not found. Please restart the server.")
    return default_user


# ---------------------------------------------------------------------------
# Strict auth - used directly only for admin endpoints
# ---------------------------------------------------------------------------

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate the JWT and return the owning User record.
    Raises UnauthorizedError for any token problem.
    """
    if not token:
        raise UnauthorizedError("Authentication required")
    try:
        payload = decode_access_token(token)
        user_id: Optional[int] = payload.get("sub")
        if user_id is None:
            raise UnauthorizedError("Invalid token payload")
    except JWTError:
        raise UnauthorizedError("Token is invalid or has expired")

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if user is None:
        raise UnauthorizedError("User no longer exists or is inactive")

    return user


def require_role(*allowed_roles: str):
    """
    Returns a FastAPI dependency that enforces role-based access.
    Always requires a valid JWT - no anonymous fallback.

    Usage:
        Depends(require_role("admin"))
        Depends(require_role("user", "admin"))
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in allowed_roles:
            raise ForbiddenError(
                f"This action requires one of the following roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker
