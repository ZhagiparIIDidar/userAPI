# app/models/user.py
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)

    # nullable — пользователь может быть создан ТОЛЬКО через OAuth,
    # без пароля вообще (нечего сравнивать при логине)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String, default="admin")

    # для мгновенной инвалидации всех refresh-токенов (logout всех сессий)
    token_version: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # связь один-ко-многим: у юзера может быть несколько привязанных провайдеров
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def has_password(self) -> bool:
        """Полезно на фронте — показывать ли форму 'установить пароль'
        для юзеров, залогиненных только через OAuth."""
        return self.password_hash is not None
