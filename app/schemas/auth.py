# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)  # обычная регистрация — пароль обязателен
    username: str | None = None
    # (для OAuth-регистрации пароль не нужен — тот путь идёт
    # через отдельный OAuth callback, а не через этот эндпоинт)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class SetPasswordIn(BaseModel):
    """Для юзеров, которые зарегались через OAuth и хотят
    завести обычный пароль (доп. способ входа)."""

    new_password: str = Field(min_length=8)
