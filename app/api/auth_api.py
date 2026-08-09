# app/api/auth.py
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn):
    if await get_user_by_email(data.email):
        raise HTTPException(400, "Email already registered")

    user = await create_user(
        email=data.email,
        password_hash=hash_password(data.password),
        username=data.username,
    )

    verify_token = create_verify_email_token(str(user.id))
    # await send_verification_email(user.email, verify_token)

    return {"detail": "Registered. Check your email to verify account."}


@router.get("/verify")
async def verify_email(token: str): ...


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
