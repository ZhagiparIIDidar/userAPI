# app/core/security.py
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Literal
import uuid

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import pwd_context, settings


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Создание токенов (подписываем PRIVATE_KEY)
# ---------------------------------------------------------------------------
def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: Literal["access", "refresh", "verify", "reset"],
    extra_claims: Optional[dict] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.PRIVATE_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: str, extra_claims: Optional[dict] = None) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
        extra_claims=extra_claims,
    )


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
        extra_claims={"ver": token_version},
    )


def create_verify_email_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(hours=settings.VERIFY_TOKEN_EXPIRE_HOURS),
        token_type="verify",
    )


def create_password_reset_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES),
        token_type="reset",
    )


# ---------------------------------------------------------------------------
# Декодирование / валидация (проверяем PUBLIC_KEY)
# ---------------------------------------------------------------------------
def decode_token(token: str, expected_type: Optional[str] = None) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, settings.PUBLIC_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        return None

    if expected_type and payload.get("type") != expected_type:
        return None

    return payload
