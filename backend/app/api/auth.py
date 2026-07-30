from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.domain import UserType
from app.db.mixins import utcnow
from app.db.session import get_db
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    AuthSessionResponse,
    FacultyUserResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RegisterRequest,
    UserPreferencesRequest,
)
from app.services.auth.email import send_password_reset_email
from app.services.auth.passwords import (
    hash_password,
    password_hash_needs_rehash,
    verify_password,
)
from app.services.auth.tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])

_INVALID_CREDENTIALS = "Invalid email or password."
_RESET_MESSAGE = "If an active account matches that email, password reset instructions were sent."


def _session_response(user: User, settings: Settings) -> AuthSessionResponse:
    token, expires_in = create_access_token(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        token_version=user.token_version,
        settings=settings,
    )
    return AuthSessionResponse(
        access_token=token,
        expires_in=expires_in,
        user=FacultyUserResponse.model_validate(user),
    )


@router.post("/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthSessionResponse:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        display_name=payload.display_name,
        institution=payload.institution,
        department=payload.department,
        password_hash=hash_password(payload.password),
        is_active=True,
        email_verified=False,
        token_version=0,
        user_type=UserType.FACULTY_MEMBER,
        preferred_language=payload.preferred_language,
        last_login_at=utcnow(),
    )
    try:
        db.add(user)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    return _session_response(user, settings)


@router.post("/login", response_model=AuthSessionResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthSessionResponse:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)

    if user.password_hash and password_hash_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    user.last_login_at = utcnow()
    db.flush()
    return _session_response(user, settings)


@router.get("/me", response_model=FacultyUserResponse)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> FacultyUserResponse:
    return FacultyUserResponse.model_validate(current_user)


@router.patch("/preferences", response_model=FacultyUserResponse)
def update_preferences(
    payload: UserPreferencesRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FacultyUserResponse:
    current_user.preferred_language = payload.preferred_language
    db.flush()
    return FacultyUserResponse.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    # Stateless access tokens are revoked through the account token version.
    # This intentionally signs the user out from all active browser sessions.
    current_user.token_version += 1
    db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
def request_password_reset(
    payload: PasswordResetRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PasswordResetRequestResponse:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    debug_reset_token: str | None = None

    if user is not None and user.is_active and user.password_hash is not None:
        now = datetime.now(UTC)
        db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        raw_token = secrets.token_urlsafe(48)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=now + timedelta(minutes=settings.password_reset_token_minutes),
        )
        db.add(reset_token)
        db.flush()
        send_password_reset_email(
            settings=settings,
            recipient=user.email,
            token=raw_token,
            language=user.preferred_language,
        )
        if settings.app_env.lower() in {"development", "test"}:
            debug_reset_token = raw_token

    return PasswordResetRequestResponse(
        message=_RESET_MESSAGE,
        debug_reset_token=debug_reset_token,
    )


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    reset_token = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if (
        reset_token is None
        or reset_token.used_at is not None
        or _as_utc(reset_token.expires_at) <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has expired.",
        )

    user = db.get(User, reset_token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has expired.",
        )

    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    reset_token.used_at = now
    db.flush()
    return MessageResponse(message="Your password has been reset. You can now sign in.")
