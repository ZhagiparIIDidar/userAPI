import uuid
import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


# --- Базовая схема с общими полями ---
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: str | None = Field(default=None, max_length=255)


# --- Схема для создания пользователя (вход от клиента) ---
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Пароль должен содержать буквы и цифры")
        return value


# --- Схема для обновления пользователя (все поля опциональны) ---
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50)
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


# --- Схема для ответа клиенту (без пароля) ---
class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


# --- Внутренняя схема (например, для работы с БД, включает хеш пароля) ---
class UserInDB(UserRead):
    hashed_password: str