"""User registration and authentication service."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.passwords import hash_password, verify_password
from app.db.models import User
from app.models.auth import (
    AuthTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    SignUpRequest,
    UserResponse,
)

# Block continued use of these defaults in production-style deploys.
INSECURE_DEFAULT_PASSWORDS = frozenset(
    {
        "admin123",
        "password",
        "changeme",
        "admin",
        "Admin123",
        "Password1",
    }
)


def is_insecure_password(password: str) -> bool:
    return password.strip() in INSECURE_DEFAULT_PASSWORDS


class AuthService:
    async def sign_up(self, session: AsyncSession, request: SignUpRequest) -> AuthTokenResponse:
        if is_insecure_password(request.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Choose a stronger password. Common default passwords are not allowed.",
            )
        user = User(
            email=request.email.lower().strip(),
            password_hash=hash_password(request.password),
            must_change_password=False,
        )
        session.add(user)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this username already exists.",
            ) from exc

        await session.refresh(user)
        return self._build_auth_response(user)

    async def login(self, session: AsyncSession, request: LoginRequest) -> AuthTokenResponse:
        result = await session.execute(
            select(User).where(User.email == request.email.lower().strip())
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )

        # Force password rotation when still using a known insecure default.
        if is_insecure_password(request.password) and not user.must_change_password:
            user.must_change_password = True
            await session.commit()
            await session.refresh(user)

        return self._build_auth_response(user)

    async def change_password(
        self,
        session: AsyncSession,
        user: User,
        request: ChangePasswordRequest,
    ) -> UserResponse:
        if not verify_password(request.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )
        if request.new_password == request.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the current password.",
            )
        if is_insecure_password(request.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Choose a stronger password. Common default passwords are not allowed.",
            )

        user.password_hash = hash_password(request.new_password)
        user.must_change_password = False
        await session.commit()
        await session.refresh(user)
        return self.to_user_response(user)

    async def get_user_by_id(self, session: AsyncSession, user_id: UUID) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    def to_user_response(self, user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
            must_change_password=bool(getattr(user, "must_change_password", False)),
            llm_daily_budget_usd=getattr(user, "llm_daily_budget_usd", None),
        )

    def _build_auth_response(self, user: User) -> AuthTokenResponse:
        token = create_access_token(str(user.id))
        return AuthTokenResponse(
            access_token=token,
            user=self.to_user_response(user),
        )
