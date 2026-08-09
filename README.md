Ниже — практическое руководство по проектированию и реализации полноценной системы управления пользователями для проекта на FastAPI. Описано: архитектура, сущности (схема БД), обязательные и дополнительные фичи, API-эндпоинты, безопасность (аутентификация/авторизация), рабочая структура проекта, рекомендуемые библиотеки, миграции, тесты и деплой.

Ключевые требования и принципы
- Безопасность: безопасное хранение паролей (bcrypt/argon2), защита токенов, валидация входа, rate limiting.
- Разделение ответственности: модели → сервисы (бизнес-логика) → зависимости (DI) → роуты → репозиторий/слой доступа к БД.
- Масштабируемость и расширяемость: роли/пермишены, email подтверждение, 2FA, логирование событий.
- Отказоустойчивость: корректная обработка ошибок, централизованный error-handling, audit trails.

Основные сущности (пример)
- User
  - id: UUID
  - email: string, unique, indexed
  - username: string, optional, unique
  - hashed_password: string
  - is_active: bool
  - is_verified: bool (email confirmed)
  - is_superuser/admin: bool
  - created_at, updated_at: datetime
  - last_login: datetime (nullable)
- Role (опционально)
  - id, name (e.g. "admin", "manager", "user")
- UserRole / RoleAssignment (m:n)
- Permission (если нужна тонкая гранулярность)
- AuditLog / UserEvent (кто, действие, когда, meta)
- TokenBlackList (для отзыва refresh-токенов, если используете JWT)

Рекомендованные технологии/библиотеки
- FastAPI
- SQLAlchemy 2 / SQLModel / Tortoise (я рекомендую SQLAlchemy/SQLModel + Alembic)
- Pydantic (для схем)
- Databases: PostgreSQL (рекомендуется), SQLite для dev
- Migrations: Alembic
- Password hashing: passlib (bcrypt/argon2)
- JWT: PyJWT / python-jose (jose рекомендуют в официальной доке FastAPI)
- Email: aiosmtplib или внешние сервисы (SendGrid, Mailgun)
- Background tasks: Celery/Redis или FastAPI BackgroundTasks для простых задач
- Optional: fastapi-users (готовое решение), OAuth2/OIDC libs for social login
- Rate limiting: slowapi / redis-based middleware
- 2FA: pyotp (TOTP)
- Testing: pytest, httpx AsyncClient, factories (factory-boy)

Архитектура проекта (пример структуры)
- app/
  - main.py
  - core/
    - config.py
    - security.py (hash, token utils)
    - events.py
  - db/
    - base.py
    - session.py
    - models.py
    - crud.py (репозиторий)
    - migrations/ (alembic)
  - api/
    - deps.py (зависимости: get_current_user, require_roles)
    - v1/
      - auth.py (login, refresh, logout)
      - users.py (register, profile, admin CRUD)
  - schemas/ (pydantic схемы: UserCreate, UserRead, UserUpdate, Token)
  - services/
    - auth_service.py
    - email_service.py
    - user_service.py
  - tests/
  - utils/
  - docs/

Основные API-эндпоинты (REST)
- POST /auth/register — регистрация (email, password, optional username). Вернуть unverified статус, отправить письмо активации.
- GET /auth/verify?token=… — подтвердить email.
- POST /auth/login — логин, возвращает access_token + refresh_token (если используете).
- POST /auth/refresh — обновление access по refresh.
- POST /auth/logout — отзывать refresh (через blacklist или менять token version у пользователях).
- POST /auth/password/forgot — отправить письмо для сброса пароля.
- POST /auth/password/reset — выполнить сброс пароля (по токену).
- GET /users/me — профиль текущего пользователя.
- PATCH /users/me — обновление профиля.
- GET /users/{id} — (admin) получить инфо.
- GET /users — (admin) лист пользователей, фильтры, пагинация.
- PUT/PATCH /users/{id}/roles — (admin) назначить роли.
- POST /users/{id}/impersonate — (admin) импсонейшн (опционально, осторожно).

Аутентификация и авторизация
- Используйте OAuth2PasswordBearer (FastAPI) + JWT (access short-lived, refresh long-lived).
- Access token: короткий срок (5–15 минут). Refresh token: несколько дней/недель.
- Подпись токенов: asymmetric (RS256) или symmetric (HS256) — для распределенных систем RS256 лучше.
- Хранение refresh: можно хранить в БД (с черным списком) или инкрементальную версию (token_version) в user модели: при логауте увеличиваете token_version, тогда старые refresh недействительны.
- Защита от атак:
  - Хешируйте пароли (bcrypt/argon2).
  - Не храните plain tokens в DB без шифрования.
  - Подтверждение email для важных операций.
  - Ограничение попыток логина (brute-force) + временная блокировка.
  - Используйте HTTPS, secure cookies (если храните токены в cookies).

Пример workflow аутентификации (JWT)
- Login: validate credentials → generate access JWT (exp=15m) + refresh JWT (exp=14d) → return.
- Subsequent requests: include Authorization: Bearer <access>.
- Refresh: provide refresh token → validate signature, check token_version or DB blacklist → issue new access (и новый refresh если нужно).

Пример модели на SQLModel / Pydantic (схематично)
- Pydantic/SQLModel UserCreate:
  - email: EmailStr
  - password: str (validate length)
- UserRead:
  - id, email, username, is_active, is_verified, created_at
- DB model:
  - hashed_password: str
  - token_version: int = 0

Пример функций безопасности (псевдокод)
- hash_password(password) -> passlib.hash
- verify_password(plain, hashed)
- create_access_token(data, expires_delta)
- create_refresh_token(data, expires_delta)
- get_current_user dependency:
  - read Authorization header, decode JWT, check exp, fetch user by id, check is_active, optional roles check.

Email подтверждение и сброс пароля
- Генерируйте одноразовый signed токен (e.g. JWT с claim type=verify or reset + exp).
- Ссылки: https://your-app/verify?token=<token>
- На сервере: decode token, найти user_id, пометить is_verified, if token expired -> send new.

Роли и пермишены
- Простая схема: role strings + role-check decorator/deps: require_roles("admin")
- Более гибкая: permissions per-resource (ACL), хранение правил в DB и проверка в зависимости от метода и ресурса.
- Рекомендуется иметь middleware или dependency для централизованной проверки.

Админ-панель
- Вариант: отдельное SPA (React/Vue) использующее admin API.
- Быстрое решение: интегрировать готовые админки (AdminJS, Forest Admin) или build-in minimal UI.
- Обязательно: audit-log на действия админов, undo/soft-delete.

Журналирование и аудит
- Записывать: логины, неудачные попытки логина, смены пароля, изменение ролей, деактивация аккаунта.
- Использовать отдельную таблицу AuditLog с полями actor_id, target_id, action, data, timestamp, ip.

Тестирование
- Unit tests для сервисов и хелперов (hashing, token utils).
- Integration tests для роутов: использовать TestClient or AsyncClient (httpx). Поднимать тестовую БД (sqlite in-memory или контейнер).
- Тесты безопасности: CSRF для cookie flow, rate limiting, brute-force.

DevOps / деплой
- Переменные окружения и секреты: храните JWT secret/keys, DB credentials в секретном хранилище (Vault, K8s Secrets, AWS Secrets Manager).
- Контейнеризация: Dockerfile + docker-compose (Postgres, Redis for Celery).
- Migrate: Alembic migrations в CI/CD pipeline.
- Мониторинг: Sentry для ошибок, Prometheus/Grafana для метрик.
- HTTPS: TLS termination на proxy/ingress (nginx, traefik).
- Обновления токенов при деплое: иметь версию токена/ключа, чтобы можно было инвалировать старые токены при необходимости.

Дополнительные функции (опционально)
- Social login (OAuth2): Google, GitHub, Facebook.
- 2FA (TOTP, SMS).
- Device/session management: список активных сессий, возможность logout со всех устройств.
- Soft delete пользователей + архивирование.
- Rate limits, IP-based restrictions
- Account lockout и notify on suspicious activity.

Пример минимального набора endpoint-реализаций (псевдо-пакет)
- POST /auth/register
- POST /auth/login
- GET /users/me
- PATCH /users/me
- POST /auth/password/forgot
- POST /auth/password/reset
- POST /auth/refresh
- POST /auth/logout
- GET /admin/users (admin only)

Короткий пример реализации зависимостей (концепт) — на Python-псевдокоде:

1) security.py
- hash_password, verify_password (passlib)
- create_access_token (jose.jwt.encode), decode_token
2) deps.py
- oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
- async def get_current_user(token=Depends(oauth2_scheme)): decode token -> get user -> check active
- async def require_admin(user=Depends(get_current_user)): if not user.is_admin: raise HTTPException(403)

Советы при старте
- Начните с минимального набора (регистрация + email verify + login + get profile).
- Сделайте тесты на эти фичи. Затем добавляйте refresh tokens, RBAC, audit.
- Подумайте о UX: подтверждение по email, уведомления при изменениях аккаунта.
- Рассмотрите fastapi-users, если хотите ускорить разработку: он покрывает много базовых сценариев.

Если хотите — могу:
- 1) Сгенерировать шаблон проекта (файлы main.py, models.py, schemas.py, auth_service.py, примеры роутов) и вернуть как архив/файлы.
- 2) Привести конкретный пример кода (реализация login/register/get_current_user) с объяснениями.
- 3) Помочь спроектировать схему ролей/пермишенов под ваш конкретный домен.

Что вам удобнее дальше? Хотите шаблон проекта (скачиваемый код) или конкретные фрагменты реализации?