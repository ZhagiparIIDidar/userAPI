# app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.security import decode_token
from app.services.users import get_user_by_id
from app.core.redis import is_token_blacklisted  # если используете blacklist
from app.db import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token, expected_type="access")
    if payload is None:
        raise credentials_exception

    # опционально: проверка blacklist (logout / отозванные токены)
    # jti = payload.get("jti")
    # if jti and await is_token_blacklisted(jti):
    #     raise credentials_exception

    user_id = payload.get("sub")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(user=Depends(get_current_user)):
    # if not user.is_verified:
    #     raise HTTPException(status_code=403, detail="Email not verified")
    # if not user.is_active:
    #     raise HTTPException(status_code=403, detail="Inactive user")
    return user


def require_admin(user=Depends(get_current_active_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
