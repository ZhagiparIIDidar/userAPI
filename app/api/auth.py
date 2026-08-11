# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_verify_email_token,
    create_password_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    RegisterIn,
    TokenPair,
    RefreshIn,
    ForgotPasswordIn,
    ResetPasswordIn,
)
from app.services import users as users_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    if await users_service.get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    if data.username and await users_service.get_user_by_username(db, data.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    user = await users_service.create_user(
        db,
        email=data.email,
        password_hash=hash_password(data.password),
        username=data.username,
    )

    verify_token = create_verify_email_token(str(user.id))
    # await send_verification_email(user.email, verify_token)

    # return {"detail": "Registered. Check your email to verify account."}
    return user


@router.get("/verify")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(token, expected_type="verify")
    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await users_service.mark_user_verified(db, payload["sub"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"detail": "Email verified successfully"}


@router.post("/login", response_model=TokenPair)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await users_service.get_user_by_email(
        db, form_data.username
    )  # username = email

    if (
        not user
        or not user.password_hash
        or not verify_password(form_data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access_token = create_access_token(str(user.id), extra_claims={"role": user.role})
    refresh_token = create_refresh_token(str(user.id), token_version=user.token_version)

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(data: RefreshIn, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = await users_service.get_user_by_id(db, payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # ключевая проверка: если версия в токене не совпадает с текущей —
    # значит был logout/смена пароля/impersonate-ревокация, токен больше не валиден
    if payload.get("ver") != user.token_version:
        raise HTTPException(status_code=401, detail="Token revoked")

    access_token = create_access_token(str(user.id), extra_claims={"role": user.role})
    new_refresh_token = create_refresh_token(
        str(user.id), token_version=user.token_version
    )
    # ротация: старый refresh больше нигде не хранится и не используется дальше

    return TokenPair(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # инвалидирует ВСЕ refresh-токены пользователя разом (все устройства/сессии)
    await users_service.bump_token_version(db, user.id)
    return {"detail": "Logged out"}


@router.post("/password/forgot")
async def forgot_password(data: ForgotPasswordIn, db: AsyncSession = Depends(get_db)):
    user = await users_service.get_user_by_email(db, data.email)
    if user:
        reset_token = create_password_reset_token(str(user.id))
        # await send_reset_email(user.email, reset_token)

    # одинаковый ответ независимо от того, найден email или нет —
    # чтобы нельзя было через этот эндпоинт узнавать зарегистрированные email
    return {"detail": "If the email exists, a reset link has been sent"}


@router.post("/password/reset")
async def reset_password(data: ResetPasswordIn, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.token, expected_type="reset")
    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await users_service.get_user_by_id(db, payload["sub"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await users_service.set_user_password(db, user, hash_password(data.new_password))
    await users_service.bump_token_version(db, user.id)  # разлогинить все старые сессии

    return {"detail": "Password reset successfully"}
