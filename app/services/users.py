# app/services/users.py
import uuid
import math

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------
async def get_user_by_id(db: AsyncSession, user_id: str | uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# List (с пагинацией и фильтрами — для admin)
# ---------------------------------------------------------------------------
async def list_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[User], int]:
    query = select(User)
    count_query = select(func.count()).select_from(User)

    if search:
        pattern = f"%{search}%"
        cond = (User.email.ilike(pattern)) | (User.username.ilike(pattern))
        query = query.where(cond)
        count_query = count_query.where(cond)

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    users = result.scalars().all()

    return list(users), total


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password_hash: str | None = None,
    username: str | None = None,
    full_name: str | None = None,
    avatar_url: str | None = None,
    is_verified: bool = False,
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        username=username,
        full_name=full_name,
        avatar_url=avatar_url,
        is_verified=is_verified,
    )
    db.add(user)
    await db.flush()  # получить user.id до commit
    await db.refresh(user)

    logger.debug(
        "User created in DB", extra={"user_id": str(user.id), "email": user.email}
    )

    return user


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------
async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user


async def set_user_password(db: AsyncSession, user: User, password_hash: str) -> User:
    user.password_hash = password_hash
    await db.flush()
    return user


async def mark_user_verified(db: AsyncSession, user_id: str | uuid.UUID) -> User | None:
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None
    user.is_verified = True
    await db.flush()
    return user


async def bump_token_version(db: AsyncSession, user_id: str | uuid.UUID) -> User | None:
    """Инвалидирует все выданные refresh-токены разом
    (logout всех сессий, смена пароля, компрометация аккаунта)."""
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None
    user.token_version += 1

    logger.info(
        "Token version bumped (sessions revoked)", extra={"user_id": str(user.id)}
    )

    await db.flush()
    return user


async def update_user_role(db: AsyncSession, user: User, role: str) -> User:
    user.role = role
    await db.flush()
    await db.refresh(user)
    return user


async def set_active_status(db: AsyncSession, user: User, is_active: bool) -> User:
    user.is_active = is_active
    await db.flush()
    return user


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
async def delete_user(db: AsyncSession, user: User) -> None:

    logger.warning("User deleted", extra={"user_id": str(user.id)})

    await db.delete(user)
    await db.flush()
