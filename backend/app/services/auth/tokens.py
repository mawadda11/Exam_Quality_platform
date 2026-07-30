from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from jwt import InvalidTokenError

from app.core.config import Settings


class AccessTokenError(ValueError):
    pass


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: UUID
    email: str
    display_name: str
    token_version: int


def create_access_token(
    *,
    user_id: UUID,
    email: str,
    display_name: str,
    token_version: int,
    settings: Settings,
) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_in_seconds = settings.auth_access_token_minutes * 60
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "name": display_name,
        "tv": token_version,
        "typ": "access",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=expires_in_seconds),
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, expires_in_seconds


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
            options={"require": ["sub", "email", "tv", "typ", "exp", "iat"]},
        )
        if payload.get("typ") != "access":
            raise AccessTokenError("Invalid access token type.")
        return AccessTokenClaims(
            user_id=UUID(str(payload["sub"])),
            email=str(payload["email"]).strip().lower(),
            display_name=str(payload.get("name") or payload["email"]).strip(),
            token_version=int(payload["tv"]),
        )
    except (InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        raise AccessTokenError("Invalid or expired access token.") from exc
