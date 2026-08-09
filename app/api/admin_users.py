# app/api/admin_users.py
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/users",
    tags=["admin-users"],
    # dependencies=[Depends(require_admin)],
)


@router.get("")
async def list_users(): ...


@router.get("/{id}")
async def get_user(id: int): ...


@router.patch("/{id}/roles")
async def update_user_roles(id: int): ...


@router.post("/{id}/impersonate")
async def impersonate_user(id: int): ...
