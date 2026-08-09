# app/api/users.py
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(): ...


@router.patch("/me")
async def update_me(): ...
