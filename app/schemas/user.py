# app/schemas/user.py
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------------------------------------------------------------------------
# Базовые/общие поля
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None


# ---------------------------------------------------------------------------
# Создание (внутреннее использование — сервисным слоем, не эндпоинтом напрямую)
# ---------------------------------------------------------------------------
class UserCreate(UserBase):
    password: str | None = Field(default=None, min_length=8)
    # None — если юзер создаётся через OAuth и пароля не имеет


# ---------------------------------------------------------------------------
# Обновление профиля (PATCH /users/me)
# ---------------------------------------------------------------------------
class UserUpdate(BaseModel):
    username: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None


# ---------------------------------------------------------------------------
# Ответ наружу — то, что видит сам пользователь (GET /users/me)
# ---------------------------------------------------------------------------
class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_verified: bool
    is_active: bool
    role: str
    has_password: bool  # фронт поймёт, показывать ли форму "задать пароль"
    created_at: datetime


# ---------------------------------------------------------------------------
# Ответ для админки (GET /users, GET /users/{id}) — чуть больше полей
# ---------------------------------------------------------------------------
class UserAdminOut(UserOut):
    updated_at: datetime
    token_version: int


# ---------------------------------------------------------------------------
# Список с пагинацией (GET /users)
# ---------------------------------------------------------------------------
class UserListOut(BaseModel):
    items: list[UserAdminOut]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Назначение ролей (PATCH /users/{id}/roles)
# ---------------------------------------------------------------------------
class UserRoleUpdate(BaseModel):
    role: str = Field(pattern="^(user|admin|moderator)$")
    # при желании можно заменить на Literal["user", "admin", "moderator"]
