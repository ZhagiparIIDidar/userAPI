# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.logging import setup_logging, get_logger
from app.db import close_db
from app.api import auth, users, admin_users

# app/main.py (добавить middleware)
from app.core.middleware import RequestLoggingMiddleware

setup_logging()  # вызывается ДО создания app и импорта роутеров с логами
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")
    await close_db()


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin_users.router)


app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
