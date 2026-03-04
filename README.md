# Trendsee MVP

Каталог трендов + асинхронная генерация контента со списанием токенов, историей, idempotency и web-интерфейсом.

### Технические требования
- Python + FastAPI
- Нормальная структура проекта:(`app/api`, `app/services`, `app/models`, `app/db`, `app/web`, `tests`)
- БД: Postgres или SQLite: (Postgres в `docker-compose`, SQLite для локальных/тестовых сценариев)
- Файлы: локально или S3/MinIO: (локальное хранение в `uploads/`)
- Асинхронность генерации: (Celery + Redis)
- Docker-compose: 

### Минимальный API из ТЗ
Поддерживаются endpoint-ы в виде из ТЗ:
- `GET /trends?active=true&type=video`
- `GET /trends/{id}`
- `POST /trends`
- `PATCH /trends/{id}`
- `POST /assets/upload`
- `POST /generations`
- `GET /generations/{id}`

Также доступны канонические API-эндпоинты с префиксом `/api` (используются в UI и тестах).

## Архитектура и стек
- FastAPI + SQLAlchemy Async
- Postgres 16
- Redis 7
- Celery worker
- Jinja2 (SSR UI)
- Alembic migrations

## Mock mode (по умолчанию)
- Провайдер генерации по умолчанию: `mock`
- Без платных API-ключей проект полностью работает
- При наличии ключа можно переключить на OpenRouter

## Быстрый запуск (Docker)

1. Скопировать env:

```bash
cp .env.example .env
```

2. Поднять стек:

```bash
docker compose up --build -d
```

3. Открыть:
- UI: `http://localhost:8000/trends`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Локальный запуск (без Docker)

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Демо-доступы
- User API key: `dev-user-key`
- Admin API key: `dev-admin-key`
- Admin web token: `admin-ui-token`

## Примеры запросов

### Тренды
```bash
curl "http://localhost:8000/trends?active=true&type=video" -H "Accept: application/json"
curl "http://localhost:8000/trends/1" -H "Accept: application/json"
```

```bash
curl -X POST "http://localhost:8000/trends" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-admin-key" \
  -d '{
    "title":"Новый тренд",
    "type":"video",
    "preview_url":"https://picsum.photos/seed/new-trend/900/1200",
    "tags":["social","reel"],
    "is_popular":false,
    "is_active":true,
    "price_tokens":35,
    "prompt_template":"Создай короткий вертикальный сценарий"
  }'
```

```bash
curl -X PATCH "http://localhost:8000/trends/1" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-admin-key" \
  -d '{"is_active": true, "is_popular": true}'
```

### Файлы
```bash
curl -X POST "http://localhost:8000/assets/upload" \
  -H "X-API-Key: dev-user-key" \
  -F "file=@./sample.jpg"
```

### Генерации
```bash
curl -X POST "http://localhost:8000/generations" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-user-key" \
  -H "Idempotency-Key: 11111111-1111-1111-1111-111111111111" \
  -d '{"trend_id":1,"prompt":"Сделай короткий сценарий","resources":[],"asset_ids":[]}'
```

```bash
curl "http://localhost:8000/generations/<generation_id>" -H "X-API-Key: dev-user-key"
```

## Плюсы из ТЗ (реализовано)
- SSE для статуса генерации: `GET /api/generations/{id}/events?api_key=...`
- История генераций: `GET /api/generations` + web-страница `/generations`
- Простая авторизация: `X-API-Key` + admin web token
- Логи/трейсинг запросов: middleware с request_id и длительностью
- Защита от повторного списания: `Idempotency-Key`

## Что упрощено и почему
- S3/MinIO не подключались: локальное хранилище `uploads/` достаточно для MVP и проще для запуска.
- Провайдер генерации по умолчанию mock: позволяет стабильную демонстрацию без внешних зависимостей и расходов.
- Сложная auth-схема (OAuth/JWT/roles) не вводилась: в ТЗ достаточно API-key/токена.
- Часть API поддерживается и в `/api/*`, и в root-path варианте из ТЗ для совместимости демо и UI.

## Тесты

```bash
pytest -q
```

Покрыты базовые сценарии:
- фильтрация/сортировка трендов
- генерация и списание токенов
- idempotency (повтор запроса без повторного списания)
- upload ассетов

