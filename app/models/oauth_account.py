# app/models/oauth_account.py
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class OAuthAccount(Base):
    """
    Связь пользователя с внешним OAuth/OIDC провайдером
    (Google, GitHub, Microsoft, Yandex и т.д.)

    Один User может иметь несколько OAuthAccount (разные провайдеры),
    но пара (provider, provider_user_id) уникальна глобально —
    один и тот же google-аккаунт не может быть привязан к двум разным юзерам.
    """

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_account"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # "google", "github", "microsoft", "yandex" ...
    provider: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # "sub" claim из OIDC id_token, либо id аккаунта у провайдера — СТАБИЛЬНЫЙ,
    # не email! (email у провайдера может меняться)
    provider_user_id: Mapped[str] = mapped_column(String, nullable=False)

    # email, который вернул провайдер (может отличаться от User.email,
    # если юзер потом сменит его у себя в профиле)
    email: Mapped[str | None] = mapped_column(String, nullable=True)

    # токены провайдера — нужны, если планируете делать запросы к его API
    # от имени пользователя (например, читать календарь Google)
    access_token: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")
