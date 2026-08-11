"""
Тесты для POST /auth/register

ПЕРЕД ЗАПУСКОМ АДАПТИРУЙТЕ ПОД ВАШ ПРОЕКТ (отмечено # TODO):
    - путь импорта FastAPI-приложения (app)
    - путь импорта модуля users_service (как он импортирован в роутере)
    - путь импорта hash_password / create_verify_email_token
    - путь импорта get_db (dependency, которую нужно переопределить)

Зависимости:
    pip install pytest pytest-asyncio httpx

Запуск:
    pytest tests/test_register.py -v
"""

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# TODO: замените на реальные пути импорта вашего проекта
# ---------------------------------------------------------------------------
from app.main import app  # TODO: путь к FastAPI приложению
from app.db import get_db  # TODO: dependency для сессии БД

# Модуль, из которого роутер импортирует users_service (как объект/модуль)
import app.services.users as users_service  # TODO

# Роутер импортирует hash_password и create_verify_email_token напрямую в свой
# namespace (например: `from app.security import hash_password`).
# Патчить нужно ИМЕННО в модуле роутера, а не в модуле-источнике, иначе monkeypatch
# не сработает (классическая ловушка с `from x import y`).
import app.api.auth as auth_router  # TODO: путь к модулю с register()

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_db_session():
    """Заглушка AsyncSession — реальные вызовы всё равно идут через мок users_service."""
    return MagicMock(name="AsyncSession")


@pytest.fixture(autouse=True)
def override_get_db(fake_db_session):
    async def _get_db():
        yield fake_db_session

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_service(monkeypatch):
    """Мокаем функции users_service там, где их использует роутер."""
    get_by_email = AsyncMock(return_value=None)
    get_by_username = AsyncMock(return_value=None)
    create_user = AsyncMock()

    monkeypatch.setattr(auth_router.users_service, "get_user_by_email", get_by_email)
    monkeypatch.setattr(
        auth_router.users_service, "get_user_by_username", get_by_username
    )
    monkeypatch.setattr(auth_router.users_service, "create_user", create_user)

    return {
        "get_user_by_email": get_by_email,
        "get_user_by_username": get_by_username,
        "create_user": create_user,
    }


@pytest.fixture(autouse=True)
def mock_security_helpers(monkeypatch):
    """hash_password и create_verify_email_token не должны реально хэшировать/создавать JWT в юнит-тестах."""
    monkeypatch.setattr(
        auth_router, "hash_password", MagicMock(side_effect=lambda pw: f"hashed:{pw}")
    )
    monkeypatch.setattr(
        auth_router,
        "create_verify_email_token",
        MagicMock(return_value="fake-verify-token"),
    )


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def make_user(id=1, email="test@example.com", username="tester", **extra):
    """Простая заглушка объекта User (ORM-модель или dataclass)."""
    user = MagicMock()
    user.id = id
    user.email = email
    user.username = username
    for k, v in extra.items():
        setattr(user, k, v)
    return user


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


async def test_register_success_with_username(client, mock_service):
    mock_service["create_user"].return_value = make_user(
        email="a@b.com", username="alice"
    )

    resp = await client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "strongpass123", "username": "alice"},
    )

    assert resp.status_code == 201
    mock_service["create_user"].assert_awaited_once()


async def test_register_success_without_username(client, mock_service):
    mock_service["create_user"].return_value = make_user(
        email="nouser@example.com", username=None
    )

    resp = await client.post(
        "/auth/register", json={"email": "nouser@example.com", "password": "pw123456"}
    )

    assert resp.status_code == 201
    # username не передан -> get_user_by_username не должен вызываться вовсе
    mock_service["get_user_by_username"].assert_not_awaited()


async def test_register_empty_string_username_skips_uniqueness_check(
    client, mock_service
):
    """
    Потенциальный баг: `if data.username` — falsy-проверка.
    Пустая строка "" не пройдёт `if data.username`, значит уникальность
    НЕ проверится, но пустой username может дойти до create_user.
    """
    mock_service["create_user"].return_value = make_user(email="x@y.com", username="")

    resp = await client.post(
        "/auth/register",
        json={"email": "x@y.com", "password": "pw123456", "username": ""},
    )

    mock_service["get_user_by_username"].assert_not_awaited()
    # Задокументируйте реальное ожидаемое поведение: 201 с username="" может быть нежелательным
    assert resp.status_code in (201, 422)


# ---------------------------------------------------------------------------
# 2. Дубликаты
# ---------------------------------------------------------------------------


async def test_register_duplicate_email(client, mock_service):
    mock_service["get_user_by_email"].return_value = make_user(email="dup@example.com")

    resp = await client.post(
        "/auth/register",
        json={
            "email": "dup@example.com",
            "password": "pw123456",
            "username": "someone",
        },
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Email already registered"
    mock_service["create_user"].assert_not_awaited()


async def test_register_duplicate_username(client, mock_service):
    mock_service["get_user_by_username"].return_value = make_user(username="taken")

    resp = await client.post(
        "/auth/register",
        json={
            "email": "fresh@example.com",
            "password": "pw123456",
            "username": "taken",
        },
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Username already taken"
    mock_service["create_user"].assert_not_awaited()


async def test_register_both_email_and_username_taken_reports_email_first(
    client, mock_service
):
    """Проверка порядка проверок: email проверяется раньше username в текущей реализации."""
    mock_service["get_user_by_email"].return_value = make_user(email="a@b.com")
    mock_service["get_user_by_username"].return_value = make_user(username="taken")

    resp = await client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "pw123456", "username": "taken"},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Email already registered"
    # username вообще не должен проверяться, раз email уже упал
    mock_service["get_user_by_username"].assert_not_awaited()


# ---------------------------------------------------------------------------
# 3. Валидация email (Pydantic-схема RegisterIn)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_email",
    [
        "not-an-email",
        "",
        "missing-at.com",
        "a@",
        "@b.com",
    ],
)
async def test_register_invalid_email_format(client, mock_service, bad_email):
    resp = await client.post(
        "/auth/register",
        json={"email": bad_email, "password": "pw123456", "username": "u"},
    )
    assert resp.status_code == 422


async def test_register_missing_email_field(client, mock_service):
    resp = await client.post(
        "/auth/register", json={"password": "pw123456", "username": "u"}
    )
    assert resp.status_code == 422


async def test_register_null_email(client, mock_service):
    resp = await client.post(
        "/auth/register", json={"email": None, "password": "pw123456"}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 4. Валидация пароля
# ---------------------------------------------------------------------------


async def test_register_missing_password_field(client, mock_service):
    resp = await client.post(
        "/auth/register", json={"email": "a@b.com", "username": "u"}
    )
    assert resp.status_code == 422


async def test_register_null_password(client, mock_service):
    resp = await client.post(
        "/auth/register", json={"email": "a@b.com", "password": None}
    )
    assert resp.status_code == 422


async def test_register_very_long_password_does_not_crash(client, mock_service):
    """
    bcrypt имеет лимит 72 байта. Если hash_password использует bcrypt напрямую
    без обрезки/предхэширования, длинный пароль может уронить сервис с 500
    вместо ожидаемого корректного поведения.
    """
    mock_service["create_user"].return_value = make_user()
    long_password = "a" * 5000

    resp = await client.post(
        "/auth/register",
        json={"email": "long@example.com", "password": long_password, "username": "u"},
    )

    assert resp.status_code in (201, 400, 422)
    assert resp.status_code != 500


# ---------------------------------------------------------------------------
# 6. Security: чувствительные данные не попадают в ответ
# ---------------------------------------------------------------------------


async def test_response_never_contains_password_hash(client, mock_service):
    """
    КРИТИЧНО: эндпоинт возвращает `user` напрямую без response_model.
    Если ORM-модель имеет атрибут password_hash и сериализатор FastAPI
    достаёт все поля объекта — хэш пароля может утечь в ответ.
    """
    user = make_user(email="s@t.com", username="uu")
    user.password_hash = "super-secret-hash"
    mock_service["create_user"].return_value = user

    resp = await client.post(
        "/auth/register",
        json={"email": "s@t.com", "password": "pw123456", "username": "uu"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert "password_hash" not in body
    assert "super-secret-hash" not in str(body)


async def test_password_is_hashed_before_reaching_service(client, mock_service):
    mock_service["create_user"].return_value = make_user()

    await client.post(
        "/auth/register",
        json={"email": "hash@example.com", "password": "plaintext-pw", "username": "u"},
    )

    _, kwargs = mock_service["create_user"].call_args
    assert kwargs["password_hash"] != "plaintext-pw"
    assert kwargs["password_hash"] == "hashed:plaintext-pw"


async def test_extra_fields_like_is_admin_are_ignored(client, mock_service):
    """Защита от mass assignment: лишние поля в теле не должны попадать в create_user."""
    mock_service["create_user"].return_value = make_user()

    await client.post(
        "/auth/register",
        json={
            "email": "mass@example.com",
            "password": "pw123456",
            "username": "u",
            "is_admin": True,
            "id": 999,
        },
    )

    _, kwargs = mock_service["create_user"].call_args
    assert "is_admin" not in kwargs
    assert "id" not in kwargs


# ---------------------------------------------------------------------------
# 8. Ошибки сервисного/инфраструктурного слоя
# ---------------------------------------------------------------------------


async def test_db_error_on_email_lookup_returns_500_without_stacktrace(
    client, mock_service
):
    """
    ТЕКУЩЕЕ ПОВЕДЕНИЕ (баг): аналогично — ошибка БД при get_user_by_email
    не перехватывается и пробрасывается наружу необработанной.

    После добавления централизованного exception handler'а (или try/except
    в самом register()) переписать на:
        resp = await client.post(...)
        assert resp.status_code == 500
        assert "connection refused" not in resp.text
    """
    mock_service["get_user_by_email"].side_effect = Exception("connection refused")

    with pytest.raises(Exception, match="connection refused"):
        await client.post(
            "/auth/register",
            json={"email": "err@example.com", "password": "pw123456", "username": "u"},
        )


async def test_create_user_unique_violation_after_precheck_race(client, mock_service):
    """
    Симуляция гонки: обе предварительные проверки прошли (None),
    но create_user падает на unique constraint в БД.

    ТЕКУЩЕЕ ПОВЕДЕНИЕ (баг): исключение из users_service ничем не перехватывается
    в register() и пробрасывается наружу необработанным — клиент получает
    голый 500 без тела/структуры (а в тестовом ASGI-транспорте это долетает
    как настоящее исключение, а не HTTP-ответ).

    Как только в register() появится обработка ошибок (try/except с возвратом
    400/409 на конфликт уникальности), этот тест нужно переписать обратно
    на обычную проверку resp.status_code — pytest.raises здесь временно,
    он документирует баг, а не желаемое поведение.
    """

    class UniqueViolation(Exception):
        pass

    mock_service["create_user"].side_effect = UniqueViolation("duplicate key value")

    with pytest.raises(UniqueViolation, match="duplicate key value"):
        await client.post(
            "/auth/register",
            json={
                "email": "race@example.com",
                "password": "pw123456",
                "username": "racer",
            },
        )


# ---------------------------------------------------------------------------
# 10. Контракт запроса/ответа
# ---------------------------------------------------------------------------


async def test_empty_body_returns_422(client, mock_service):
    resp = await client.post("/auth/register", content="")
    assert resp.status_code == 422


async def test_malformed_json_returns_422(client, mock_service):
    resp = await client.post(
        "/auth/register",
        content="{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


async def test_verify_token_creation_does_not_block_success(client, mock_service):
    mock_service["create_user"].return_value = make_user(id=42)

    resp = await client.post(
        "/auth/register",
        json={"email": "verify@example.com", "password": "pw123456", "username": "u"},
    )

    assert resp.status_code == 201
    auth_router.create_verify_email_token.assert_called_once_with("42")


# ---------------------------------------------------------------------------
# 7. Конкурентность (реальная проверка нужна на живой БД с unique constraint,
#    здесь — только демонстрация, что эндпоинт не падает при параллельных вызовах)
# ---------------------------------------------------------------------------


async def test_concurrent_requests_do_not_crash_endpoint(client, mock_service):
    mock_service["create_user"].return_value = make_user(
        email="c@r.com", username="concurrent"
    )

    payload = {"email": "c@r.com", "password": "pw123456", "username": "concurrent"}
    r1, r2 = await asyncio.gather(
        client.post("/auth/register", json=payload),
        client.post("/auth/register", json=payload),
    )

    assert r1.status_code in (201, 400, 409)
    assert r2.status_code in (201, 400, 409)
