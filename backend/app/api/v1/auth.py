"""Authentication API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_user_record
from app.db.models import User
from app.db.session import get_db_session
from app.models.auth import (
    AuthTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    SignUpRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()


@router.post("/signup", response_model=AuthTokenResponse)
async def sign_up(
    request: SignUpRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    return await auth_service.sign_up(session, request)


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    return await auth_service.login(session, request)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user


@router.post("/change-password", response_model=UserResponse)
async def change_password(
    request: ChangePasswordRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user_record),
) -> UserResponse:
    return await auth_service.change_password(session, user, request)
