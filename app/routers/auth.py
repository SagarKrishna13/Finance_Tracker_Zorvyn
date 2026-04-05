"""
Auth router - /auth/register and /auth/login.

Thin by design: validate input (Pydantic), call service, return response.
No business logic lives here.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse
from app.schemas.common import SuccessResponse
from app.services import user_service

router = APIRouter()


@router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=201,
    summary="Register a new user",
)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    user = user_service.register_user(db, payload)
    return {"success": True, "data": user, "message": "Account created successfully"}


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    summary="Login and receive a JWT",
)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    result = user_service.authenticate_user(db, payload.email, payload.password)
    return {"success": True, "data": result, "message": "Login successful"}
