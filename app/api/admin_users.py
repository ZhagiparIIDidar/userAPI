# app/api/admin_users.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.deps import require_admin
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.user import UserAdminOut, UserListOut, UserRoleUpdate
from app.services import users as users_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["admin-users"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=UserListOut)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await users_service.list_users(
        db,
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        is_active=is_active,
    )
    return UserListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{id}", response_model=UserAdminOut)
async def get_user(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await users_service.get_user_by_id(db, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{id}/roles", response_model=UserAdminOut)
async def update_user_roles(
    id: uuid.UUID,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    user = await users_service.get_user_by_id(db, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(
        "User role updated by admin",
        extra={
            "admin_id": str(admin.id),
            "target_user_id": str(user.id),
            "new_role": data.role,
        },
    )

    return await users_service.update_user_role(db, user, data.role)


@router.post("/{id}/impersonate")
async def impersonate_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot impersonate yourself")

    target = await users_service.get_user_by_id(db, id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot impersonate another admin")

    if not target.is_active:
        raise HTTPException(
            status_code=400, detail="Cannot impersonate an inactive user"
        )

    # обязательно аудит-лог: кто, кого, когда — без этого impersonate нельзя выпускать в прод
    # await audit_log.record(
    #     action="impersonate",
    #     actor_id=admin.id,
    #     target_id=target.id,
    # )
    logger.warning(  # warning, не info — это чувствительное действие, должно быть заметно в логах
        "Admin impersonated user",
        extra={"admin_id": str(admin.id), "target_user_id": str(target.id)},
    )

    access_token = create_access_token(
        str(target.id),
        extra_claims={
            "role": target.role,
            "impersonated_by": str(admin.id),  # обязательно помечаем токен как "чужой"
        },
    )

    logger.warning(  # warning, не info — это чувствительное действие, должно быть заметно в логах
        "Admin impersonated user",
        extra={"admin_id": str(admin.id), "target_user_id": str(target.id)},
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "impersonated_user_id": str(target.id),
    }
