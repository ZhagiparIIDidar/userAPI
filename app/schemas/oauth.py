# app/schemas/oauth.py
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


# ---------------------------------------------------------------------------
# Информация о привязанном провайдере — то, что видит сам пользователь
# в своём профиле (например GET /users/me/oauth-accounts)
# ---------------------------------------------------------------------------
class OAuthAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    email: EmailStr | None = None
    created_at: datetime
    # access_token/refresh_token НЕ отдаём наружу — секреты провайдера


# ---------------------------------------------------------------------------
# Данные, которые парсим из userinfo/id_token провайдера
# (используется внутри сервисного слоя при обработке callback)
# ---------------------------------------------------------------------------
class OAuthUserInfo(BaseModel):
    sub: str  # стабильный id пользователя у провайдера
    email: EmailStr | None = None
    email_verified: bool = False
    name: str | None = None
    picture: str | None = None


# ---------------------------------------------------------------------------
# Query-параметры callback-эндпоинта (GET /auth/{provider}/callback)
# ---------------------------------------------------------------------------
class OAuthCallbackParams(BaseModel):
    code: str
    state: str | None = None
