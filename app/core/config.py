from pathlib import Path

from passlib.context import CryptContext
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# JWT / Authentication Config
# ---------------------------------------------------------------------------


class AuthJWT(BaseModel):
    ALGORITHM: str = "RS256"

    PRIVATE_KEY_PATH: Path = BASE_DIR / "keys" / "private.pem"
    PUBLIC_KEY_PATH: Path = BASE_DIR / "keys" / "public.pem"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    VERIFY_TOKEN_EXPIRE_HOURS: int = 24
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def PRIVATE_KEY(self) -> str:
        return self.PRIVATE_KEY_PATH.read_text()

    @property
    def PUBLIC_KEY(self) -> str:
        return self.PUBLIC_KEY_PATH.read_text()


# ---------------------------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ---------------------------------------------------------------------------
# Application Config
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    DB_ECHO: bool = False  # логировать SQL-запросы (только для дебага)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    auth_jwt: AuthJWT = AuthJWT()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def DATABASE_URL_asyncpg(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASS}@"
            f"{self.DB_HOST}:{self.DB_PORT}/"
            f"{self.DB_NAME}"
        )

    @property
    def DATABASE_URL_psycopg2(self) -> str:
        return (
            f"postgresql+psycopg2://"
            f"{self.DB_USER}:{self.DB_PASS}@"
            f"{self.DB_HOST}:{self.DB_PORT}/"
            f"{self.DB_NAME}"
        )


settings = Settings()
