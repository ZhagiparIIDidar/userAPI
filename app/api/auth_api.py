# app/api/auth.py
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(): ...


@router.get("/verify")
async def verify_email(): ...


@router.post("/login")
async def login(): ...


@router.post("/refresh")
async def refresh_token(): ...


@router.post("/logout")
async def logout(): ...


@router.post("/password/forgot")
async def forgot_password(): ...


@router.post("/password/reset")
async def reset_password(): ...
