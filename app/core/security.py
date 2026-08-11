# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
import uuid

from jose import jwt, JWTError
import bcrypt

from app.core.config import settings


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        raise ValueError("Password is too long (max 72 bytes)")

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


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
    return jwt.encode(
        payload, settings.auth_jwt.PRIVATE_KEY, algorithm=settings.auth_jwt.ALGORITHM
    )


def create_access_token(user_id: str, extra_claims: Optional[dict] = None) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.auth_jwt.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
        extra_claims=extra_claims,
    )


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.auth_jwt.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
        extra_claims={"ver": token_version},
    )


def create_verify_email_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(hours=settings.auth_jwt.VERIFY_TOKEN_EXPIRE_HOURS),
        token_type="verify",
    )


def create_password_reset_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.auth_jwt.RESET_TOKEN_EXPIRE_MINUTES),
        token_type="reset",
    )


# ---------------------------------------------------------------------------
# Декодирование / валидация (проверяем PUBLIC_KEY)
# ---------------------------------------------------------------------------
def decode_token(token: str, expected_type: Optional[str] = None) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt.PUBLIC_KEY,
            algorithms=[settings.auth_jwt.ALGORITHM],
        )
    except JWTError:
        return None

    if expected_type and payload.get("type") != expected_type:
        return None

    return payload
