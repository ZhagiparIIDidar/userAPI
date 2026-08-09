# app/services/oauth_accounts.py
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_account import OAuthAccount


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------
async def get_oauth_account(
    db: AsyncSession, provider: str, provider_user_id: str
) -> OAuthAccount | None:
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_oauth_accounts_for_user(
    db: AsyncSession, user_id: str | uuid.UUID
) -> list[OAuthAccount]:
    result = await db.execute(
        select(OAuthAccount).where(OAuthAccount.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_oauth_account_by_id(
    db: AsyncSession, account_id: str | uuid.UUID
) -> OAuthAccount | None:
    return await db.get(OAuthAccount, account_id)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
async def create_oauth_account(
    db: AsyncSession,
    *,
    user_id: str | uuid.UUID,
    provider: str,
    provider_user_id: str,
    email: str | None = None,
    access_token: str | None = None,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
) -> OAuthAccount:
    account = OAuthAccount(
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


# ---------------------------------------------------------------------------
# Update (обновление токенов провайдера после refresh, ре-логина и т.п.)
# ---------------------------------------------------------------------------
async def update_oauth_tokens(
    db: AsyncSession,
    account: OAuthAccount,
    *,
    access_token: str | None = None,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
) -> OAuthAccount:
    if access_token is not None:
        account.access_token = access_token
    if refresh_token is not None:
        account.refresh_token = refresh_token
    if expires_at is not None:
        account.expires_at = expires_at

    await db.flush()
    return account


# ---------------------------------------------------------------------------
# Delete (отвязать провайдера от аккаунта)
# ---------------------------------------------------------------------------
async def delete_oauth_account(db: AsyncSession, account: OAuthAccount) -> None:
    await db.delete(account)
    await db.flush()


async def unlink_provider(
    db: AsyncSession, user_id: str | uuid.UUID, provider: str
) -> bool:
    """Удаляет привязку конкретного провайдера у юзера. Возвращает True, если удалили."""
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == provider,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        return False

    await db.delete(account)
    await db.flush()
    return True
