# app/schemas/__init__.py
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserOut,
    UserAdminOut,
    UserListOut,
    UserRoleUpdate,
)
from app.schemas.oauth import OAuthAccountOut, OAuthUserInfo, OAuthCallbackParams
from app.schemas.auth import (
    RegisterIn,
    LoginIn,
    TokenPair,
    RefreshIn,
    ForgotPasswordIn,
    ResetPasswordIn,
    SetPasswordIn,
)

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserOut",
    "UserAdminOut",
    "UserListOut",
    "UserRoleUpdate",
    "OAuthAccountOut",
    "OAuthUserInfo",
    "OAuthCallbackParams",
    "RegisterIn",
    "LoginIn",
    "TokenPair",
    "RefreshIn",
    "ForgotPasswordIn",
    "ResetPasswordIn",
    "SetPasswordIn",
]
