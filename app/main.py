from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.logging import setup_logging, get_logger
from app.db import close_db
from app.api import auth, users, admin_users
from app.core.middleware import RequestLoggingMiddleware

# 1. Настраиваем логи ДО создания приложения
setup_logging()
logger = get_logger(__name__)


# 2. Определяем жизненный цикл приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield  # В этой точке приложение работает и принимает запросы
    logger.info("Application shutdown")
    await close_db()  # Закрываем соединение с Postgres при выключении


# 3. Создаем ОДИН экземпляр FastAPI
app = FastAPI(lifespan=lifespan)

# 4. Добавляем Middleware (логирование входящих запросов)
app.add_middleware(RequestLoggingMiddleware)

# 5. Подключаем роутеры эндпоинтов
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin_users.router)
