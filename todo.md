Codex Agent MD: Trendsee MVP “Каталог трендов → Генерация” (FastAPI + Postgres + Celery + OpenRouter)
0) Контекст и цель (пересказ ТЗ как спецификация)
Обязательное ограничение: только MOCK по умолчанию (без платных API)

Компания не предоставляет ключ OpenRouter, а использовать личные деньги на API нельзя. Поэтому:

По умолчанию проект всегда работает в MOCK-режиме (никаких внешних запросов).

Реальный провайдер (OpenRouter) реализовать опционально, но выключенным по умолчанию.

Все end-to-end сценарии (каталог → генерация → статус → результат → списание токенов) должны работать полностью в mock-режиме.

Переключение на OpenRouter допускается только при наличии OPENROUTER_API_KEY и явном MODEL_PROVIDER=openrouter.

В раздел “ModelProvider / Провайдер моделей” (как требования к реализации)

Провайдер моделей: обязательный MockProvider

Реализовать интерфейс ModelProvider и две реализации:

MockProvider (default): не делает HTTP запросов, имитирует задержку 1–3 сек, возвращает детерминированный текст результата. Используется всегда, если MODEL_PROVIDER=mock или отсутствует OPENROUTER_API_KEY.

OpenRouterProvider (optional): используется только если MODEL_PROVIDER=openrouter и задан OPENROUTER_API_KEY. В противном случае приложение должно стартовать без ошибок и использовать MockProvider.

Требование: docker-compose и тесты должны проходить без OPENROUTER_API_KEY.

В блок ENV/README (чтобы запуск был понятен)

Добавь в .env.example:

MODEL_PROVIDER=mock

OPENROUTER_API_KEY= (не нужен для сдачи, по умолчанию пусто)
OPENROUTER_MODEL= (опционально)

И в README секцию:

Mock режим (по умолчанию)

Проект запускается без платных ключей. Генерации выполняются через MockProvider и возвращают тестовый результат, но вся логика статусов/очереди/списания токенов работает как в продакшене.

Нужно собрать мини‑продукт (MVP): каталог трендов (карточки с фото/видео превью) → переход в экран генерации → отправка генерации в провайдер моделей (желательно OpenRouter) → получение результата. Должен быть админ‑интерфейс для ручного добавления трендов и включения/выключения. Должны быть токены/баланс и списание стоимости при запуске генерации. UI обязан быть адаптивным (десктоп + мобильный). 

🧪 Тестовое задание_ “Каталог т…

🧪 Тестовое задание_ “Каталог т…

Минимальный API обязателен: тренды (GET list + GET one + POST + PATCH), upload ассетов, генерации (POST create + GET status/result). Асинхронность генерации желательна через Celery/RQ; Docker-compose очень желательно. Плюсы: SSE/WebSocket статус, история генераций, простая авторизация, логи/трейсинг, идемпотентность списания. 

🧪 Тестовое задание_ “Каталог т…

Референс UX: телеграм-бот (каталог → карточка → генерация). 

🧪 Тестовое задание_ “Каталог т…

1) Definition of Done (жёсткие критерии приёмки)

Считай задачу выполненной, только если выполняются пункты ниже.

UI (десктоп + мобилка):

Есть кликабельный каталог трендов (удобный на телефоне).

Есть карточка/страница тренда и переход в генерацию.

На генерации есть форма ввода prompt, материалов (ссылки+заметки), upload фото/видео, кнопка “Сгенерировать”, отображение “спишется N токенов”.

Статус генерации визуально обновляется: queued → running → done/failed.

Результат отображается на экране.

Тренды:

Список/грид трендов.

Карточка тренда показывает: название, тип (photo/video), превью, флаги active/popular, стоимость в токенах.

Админка:

Можно создать тренд руками: title, type, preview, tags, is_popular, is_active, price_tokens.

Можно активировать/деактивировать тренд.

Редактирование тренда — желательно (необязательно, но делаем).

Генерации + деньги:

При POST /generations происходит списание токенов с баланса.

Недостаточно токенов → генерация не запускается, баланс не уходит в минус.

Защита от повторного списания: идемпотентность (Idempotency-Key).

Провайдер моделей:

Есть слой ModelProvider.

Есть реализация OpenRouter (и mock‑провайдер для разработки/тестов без ключа).

Техническое:

Python + FastAPI.

Нормальная структура проекта.

БД Postgres (в docker-compose). Допускается SQLite для тестов.

Файлы локально (в volume).

Асинхронная генерация: Celery + Redis (как “плюс” из ТЗ).

docker-compose поднимает весь стек одной командой.

2) Архитектура (что именно строим)
2.1 Компоненты

Backend API (FastAPI):

REST API по минимальному списку.

Серверные HTML страницы (Jinja2) для UI/админки (чтобы не тащить отдельный фронтенд).

Static + uploads (локально).

SSE endpoint для статуса генерации (как плюс).

Worker (Celery):

Обрабатывает генерации асинхронно.

Обновляет статусы в БД.

Вызывает ModelProvider (OpenRouter) через httpx.

Postgres:

Хранит тренды, ассеты, генерации, пользователей/баланс, ledger транзакций, идемпотентные ключи.

Redis:

Broker для Celery.

(Опционально) канал/кэш статусов, но достаточно БД + SSE polling.

2.2 Основные потоки

Поток A: Админ добавляет тренд

Админ UI → POST /trends (или серверный action) → запись Trend + preview Asset.

Админ toggles is_active → PATCH /trends/{id}.

Поток B: Пользователь запускает генерацию

UI: выбирает тренд → форма → загружает файлы → нажимает “Сгенерировать”.

Backend:

сохраняет файлы в uploads + пишет Asset записи;

в транзакции: проверяет баланс; создаёт Generation(status=queued); списывает токены; пишет ledger; пишет idempotency record;

отправляет Celery task generation_run(generation_id).

Worker:

ставит status=running;

вызывает ModelProvider.generate();

сохраняет result + метаданные; ставит status=done или failed.

UI:

получает generation_id, открывает страницу статуса;

подписывается на SSE /generations/{id}/events и обновляет UI.

2.3 Почему такой выбор

Jinja2 UI закрывает требование адаптивного интерфейса быстрее и надёжнее, чем отдельный Next/React, и одновременно сохраняет “нормальную структуру проекта”.

Celery+Redis закрывает “плюс” по асинхронности и масштабируемости.

Ledger + идемпотентность закрывают финансовую корректность.

3) Модель данных (БД) — строго и подробно
3.1 Таблицы

users

id (PK, int/bigint)

api_key (unique, text) — простая авторизация

is_admin (bool)

token_balance (int, >=0)

created_at, updated_at (timestamptz)

Индексы:

unique(api_key)

trends

id (PK)

title (text, not null)

type (enum: photo|video)

preview_asset_id (FK assets.id, nullable) и/или preview_url (text, nullable)

tags (jsonb array of strings) или text[] (если удобно)

is_popular (bool)

is_active (bool)

price_tokens (int, >=0)

prompt_template (text, nullable) — “как генерировать” (расширение сверх ТЗ)

created_at, updated_at

Индексы:

(is_active, type)

gin(tags) если jsonb

assets

id (PK)

kind (enum: image|video|other)

original_filename (text)

storage_path (text) — относительный путь в uploads

mime_type (text)

size_bytes (bigint)

sha256 (text, nullable)

created_at

Индексы:

(sha256) (не unique, но полезно)

generations

id (PK, uuid или bigint; предпочтительно uuid)

user_id (FK users.id)

trend_id (FK trends.id)

prompt (text)

resources (jsonb) — список объектов {url, note}

status (enum: queued|running|done|failed)

price_tokens (int) — зафиксированная цена на момент запуска

provider (text) — openrouter/mock

model (text) — имя модели

result_text (text, nullable)

result_json (jsonb, nullable) — если вернём структурированный ответ

error_message (text, nullable)

created_at, updated_at, started_at, finished_at

Индексы:

(user_id, created_at desc)

(trend_id, created_at desc)

(status)

generation_assets (M2M)

generation_id (FK generations.id)

asset_id (FK assets.id)

role (text nullable) — например “input”
PK составной: (generation_id, asset_id)

token_transactions (ledger)

id (PK)

user_id (FK)

generation_id (FK nullable)

amount (int) — отрицательное списание, положительное пополнение

balance_before (int)

balance_after (int)

reason (text) — “generation_charge”, “refund”, “admin_topup”

created_at

Индексы:

(user_id, created_at desc)

(generation_id)

idempotency_keys

id (PK)

user_id (FK)

key (text) — Idempotency-Key

request_hash (text) — хеш body для защиты от reuse с другим payload

generation_id (FK)

created_at
Unique:

(user_id, key)

3.2 Инварианты (обязательные условия)

token_balance никогда не < 0.

При создании генерации:

price_tokens копируется из тренда (фиксация цены).

В ledger создаётся запись списания.

Если celery enqueue упал — делаем fail+refund (компенсация) или явно логируем и оставляем queued (лучше компенсация).

Идемпотентность:

Если пришёл повторный POST /generations с тем же Idempotency-Key и тем же request_hash — возвращаем уже созданную генерацию, не списываем повторно.

Если ключ тот же, но payload другой — 409 Conflict.

4) API контракт (минимальный + расширения)
4.1 Авторизация

Заголовок: X-API-Key: <key>

Для:

POST/PATCH /trends — только admin

POST /generations — любой пользователь

POST /assets/upload — любой пользователь

GET /trends — публично (или тоже под ключ, но лучше публично)

GET /generations/{id} — только владелец или admin

4.2 Trends

GET /trends?active=true&type=video&popular=true&tag=fun&limit=20&offset=0
Response 200:

{
  "items": [
    {
      "id": "…",
      "title": "…",
      "type": "video",
      "preview_url": "/uploads/…",
      "tags": ["…"],
      "is_popular": true,
      "is_active": true,
      "price_tokens": 30
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 123
}

GET /trends/{id}
Response 200: Trend detail (включая prompt_template, если есть)

POST /trends (admin)
Request:

{
  "title": "Hot Trend",
  "type": "photo",
  "preview_asset_id": "…",
  "preview_url": null,
  "tags": ["tiktok", "style"],
  "is_popular": false,
  "is_active": true,
  "price_tokens": 30,
  "prompt_template": "…"
}

PATCH /trends/{id} (admin)
Request (частичное обновление):

{ "is_active": false }
4.3 Assets

POST /assets/upload (multipart/form-data)

field: file (required)
Response:

{
  "id": "…",
  "url": "/uploads/…",
  "mime_type": "image/png",
  "size_bytes": 12345
}

Требования:

ограничить размер (например 25MB) и типы (image/, video/).

безопасные имена, защита от path traversal.

4.4 Generations

POST /generations (списание + постановка в очередь)
Headers:

X-API-Key

Idempotency-Key: <uuid> (рекомендуется)

Request:

{
  "trend_id": "…",
  "prompt": "Сделай так-то…",
  "resources": [
    {"url":"https://…", "note":"референс 1"}
  ],
  "asset_ids": ["…", "…"]
}

Response 201:

{
  "id": "…",
  "status": "queued",
  "price_tokens": 30,
  "balance_after": 970
}

Ошибки:

402 Payment Required: недостаточно токенов

409 Conflict: Idempotency-Key reuse с другим payload

404: trend not found / asset not found

GET /generations/{id}
Response 200:

{
  "id":"…",
  "status":"running",
  "trend": { "id":"…", "title":"…", "type":"video" },
  "prompt":"…",
  "resources":[…],
  "assets":[{"id":"…","url":"…"}],
  "price_tokens":30,
  "result_text": null,
  "error_message": null,
  "created_at":"…",
  "started_at":"…",
  "finished_at": null
}

SSE (плюс): GET /generations/{id}/events
События:

event: status

data: {"status":"running","updated_at":"…"}

event: done

data: {"status":"done","result_text":"…"}

История (плюс): GET /generations?mine=true&limit=20&offset=0

Баланс (плюс): GET /me
Response:

{"user_id":"…","token_balance":970,"is_admin":false}
5) ModelProvider слой
5.1 Интерфейс

ModelProvider.generate(trend, prompt, resources, assets) -> GenerationOutput
Где GenerationOutput:

result_text: str

raw: dict (сырые метаданные)

model: str

provider: str

5.2 OpenRouterProvider

ENV: OPENROUTER_API_KEY, OPENROUTER_MODEL

Endpoint: OpenRouter Chat Completions

Таймауты, retries (tenacity), корректная обработка ошибок.

Политика prompt‑сборки:

system: “Ты ассистент Trendsee. Верни итог в Markdown…”

user: включает:

Trend title/type/tags

Trend prompt_template (если есть)

пользовательский prompt

resources (url+note)

список asset URLs (без пересылки самих файлов, чтобы не усложнять)

5.3 MockProvider (обязателен)

Если нет ключа — возвращает детерминированный текст (и имитирует задержку 1–2 сек).
Использовать для тестов и локального демо.

6) Асинхронность: Celery
6.1 Задача

run_generation(generation_id: str)
Шаги:

Загрузить generation + trend + assets.

Update: status=running, started_at=now()

Call provider.generate(...)

Update:

done: status=done, result_text, model/provider, finished_at

failed: status=failed, error_message, finished_at

Логировать ключевые точки.

6.2 Надёжность

Ретраи в задаче (например 2–3) только для сетевых ошибок, но не для ошибок валидации.

Идемпотентность таски: если статус уже done/failed — просто выйти.

7) UI (Server-side) — страницы и требования

Требование ТЗ: адаптив и удобный клик на телефоне. 

🧪 Тестовое задание_ “Каталог т…

Реализация: Jinja2 + минимальный CSS (без тяжёлых фреймворков) + чуть JS для SSE/динамики.

7.1 Публичные страницы

/ или /trends

grid карточек (responsive: 1 колонка mobile, 2 tablet, 3–4 desktop)

фильтры: type (photo/video), active (по умолчанию true), popular

карточка: preview (img/video), title, type badge, flags, цена “N токенов”

клик ведёт на /trends/{id}

/trends/{id}

крупное превью

теги, цена, статус active/popular

кнопка “Перейти к генерации”

/trends/{id}/generate

форма:

textarea prompt

resources textarea (каждая строка: URL | note)

upload multiple (image/video)

показывать: “Спишется N токенов” + текущий баланс

submit

/generations/{id}

статус + прогресс UI

подключение SSE:

пока queued/running — показывать индикатор

когда done — показать result_text (и кнопку copy)

когда failed — показать error_message

/generations (плюс)

история генераций (последние 20) с фильтром по тренду

7.2 Админские страницы

Защита: простой admin token (ENV ADMIN_TOKEN) через cookie или заголовок, либо BasicAuth.

/admin/trends

таблица/список трендов

кнопка “Создать”

toggle is_active / is_popular (быстрое включение/выключение)

/admin/trends/new

форма:

title

type (select)

preview: upload file или url

tags (comma-separated)

is_popular checkbox

is_active checkbox

price_tokens number

prompt_template textarea (расширение)

submit → create trend → redirect to list

/admin/trends/{id}/edit (желательно)

редактирование всех полей

7.3 CSS требования

mobile-first

кнопки минимум 44px высота

превью карточек фиксированной высоты (object-fit: cover)

безопасные состояния ошибок.

8) Структура репозитория (обязательная “нормальная структура проекта”)

Предложенная структура (не менять без причины):

app/
  main.py
  core/
    config.py
    logging.py
    security.py
    errors.py
  db/
    session.py
    base.py
    migrations/          (alembic)
    init_db.py           (seed: admin user + demo trends)
  models/
    user.py
    trend.py
    asset.py
    generation.py
    token_transaction.py
    idempotency_key.py
  schemas/
    trend.py
    asset.py
    generation.py
    user.py
    common.py
  services/
    trends.py
    assets.py
    billing.py
    generations.py
    providers/
      base.py
      openrouter.py
      mock.py
  api/
    deps.py
    routes/
      trends.py
      assets.py
      generations.py
      me.py
  web/
    views.py
    templates/
      base.html
      trends_list.html
      trend_detail.html
      generate_form.html
      generation_status.html
      admin_trends.html
      admin_trend_form.html
    static/
      css/app.css
      js/app.js
  tasks/
    celery_app.py
    generation_tasks.py

docker/
  Dockerfile
docker-compose.yml
requirements.txt
.env.example
README.md
tests/
  test_trends.py
  test_generations_billing.py
  test_idempotency.py
9) Docker / окружение
9.1 docker-compose services

api:

build: Dockerfile

env: DATABASE_URL, REDIS_URL, OPENROUTER_API_KEY, etc.

volumes: ./uploads:/app/uploads

ports: 8000:8000

worker:

same image

command: celery -A app.tasks.celery_app worker -l INFO

depends_on: redis, db

db: postgres:16

volume pgdata

redis: redis:7

(опционально) flower для Celery мониторинга

9.2 ENV (.env.example)

Минимум:

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/trendsee

REDIS_URL=redis://redis:6379/0

CELERY_BROKER_URL=${REDIS_URL}

CELERY_RESULT_BACKEND=${REDIS_URL}

UPLOAD_DIR=/app/uploads

MAX_UPLOAD_MB=25

BASE_URL=http://localhost:8000

OPENROUTER_API_KEY=... (можно пустым → mock)

OPENROUTER_MODEL=openai/gpt-4o-mini (или другой)

DEFAULT_USER_API_KEY=dev-user-key

DEFAULT_ADMIN_API_KEY=dev-admin-key

INITIAL_TOKEN_BALANCE=1000

ADMIN_TOKEN=admin-ui-token

10) Детальный план работ (TODO для Codex) — выполнять сверху вниз
Phase 1 — Bootstrap (скелет проекта)

 Создать репозиторий и структуру директорий как в разделе 8.

 Добавить requirements.txt:

fastapi, uvicorn[standard]

pydantic, pydantic-settings

sqlalchemy[asyncio], asyncpg

alembic

python-multipart, aiofiles

jinja2

httpx, tenacity

celery, redis

pytest, pytest-asyncio, httpx (для тестов)

 Настроить app/main.py: FastAPI app, routers (api + web), static mounts, uploads mount, health endpoint.

 Настроить конфиг core/config.py через pydantic-settings.

 Настроить логирование core/logging.py (единый формат, request_id middleware).

Phase 2 — База данных + миграции

 Поднять SQLAlchemy Async engine/session (db/session.py).

 Описать модели SQLAlchemy (раздел 3).

 Поднять Alembic:

 alembic.ini + migrations env.py

 первая миграция создаёт все таблицы

 Seed (db/init_db.py):

 создать admin user и regular user с api_key из env

 выставить initial token_balance

 создать 3–5 демо трендов (с placeholder preview_url или с embedded demo assets)

Phase 3 — Security/Auth (API-key)

 core/security.py: verify api key, admin check.

 api/deps.py:

 get_current_user по X-API-Key

 require_admin

 Единый формат ошибок core/errors.py:

401/403/404/409/402 и JSON body {code, message, details?}

Phase 4 — Assets upload

 services/assets.py:

 validate size/mime

 safe filename (uuid)

 save to UPLOAD_DIR (aiofiles)

 create Asset record

 api/routes/assets.py: POST /assets/upload (multipart)

 Добавить static mount /uploads на UPLOAD_DIR.

Phase 5 — Trends API + Admin CRUD

 services/trends.py:

list with filters (active/type/popular/tag/search)

get by id

create

update (patch)

 api/routes/trends.py: endpoints из ТЗ.

 Валидация Pydantic schemas (trend create/update/out).

Phase 6 — Billing + Idempotency

 services/billing.py:

 debit_for_generation(user_id, amount, generation_id) в транзакции с SELECT … FOR UPDATE

 ledger запись

 models/idempotency_key.py + сервис:

 compute request_hash (sha256 от canonical json)

 check existing by (user_id, key)

 handle same payload → return existing generation

 different payload → 409

 Unit tests на двойной POST /generations.

Phase 7 — Generations API (create/status)

 services/generations.py:

 create_generation(trend_id, prompt, resources, asset_ids, idempotency_key)

 get_generation (access control)

 list_generations (history)

 api/routes/generations.py:

POST /generations

GET /generations/{id}

(plus) GET /generations (history)

 Реализовать статусы queued/running/done/failed строго.

Phase 8 — Celery worker + Provider

 tasks/celery_app.py:

конфиг broker/backend из env

 services/providers/base.py интерфейс

 services/providers/openrouter.py:

httpx async client, retries, timeouts

формирование prompt

 services/providers/mock.py

 tasks/generation_tasks.py:

задача run_generation, обновление статуса, сохранение результата

Phase 9 — SSE для статуса (плюс)

 api/routes/generations.py или отдельный router:

GET /generations/{id}/events (SSE)

реализация: polling БД раз в 0.8–1.2 сек, отправка события при изменении status/updated_at

 UI страница статуса использует EventSource.

Phase 10 — Web UI (Jinja2)

 web/views.py:

/trends (каталог)

/trends/{id} (детали)

/trends/{id}/generate (форма)

POST action generate (серверный) → создаёт generation и redirect на /generations/{id}

/generations/{id} (статус+результат)

/admin/trends (+ new/edit)

 templates + static css/js

 mobile-first адаптивность:

карточки, кнопки, формы.

Phase 11 — Dockerization

 docker/Dockerfile:

multi-stage (опционально)

запуск uvicorn

 docker-compose.yml (api, worker, db, redis)

 Проверка: docker-compose up --build поднимает всё, миграции применяются автоматически (entrypoint скрипт) или командой README.

Phase 12 — README + Report template

 README:

how to run (docker-compose)

seed/demo credentials (API keys)

curl примеры для всех endpoint’ов

описание упрощений

 REPORT.md шаблон:

потраченное время

инструменты

модель/провайдер

расход токенов/$

Phase 13 — Тесты (минимум, но реальные)

 test_idempotency.py: повторный запрос не списывает дважды

 test_billing.py: недостаточно токенов → 402, генерация не создана

 test_trends_filters.py: фильтры active/type работают

 (опционально) test_assets_upload.py

11) Алгоритмы, которые нельзя реализовать “примерно”
11.1 Списание токенов (атомарность)

Внутри транзакции:

SELECT user FOR UPDATE

если balance < price → raise 402

INSERT generation(status=queued, price_tokens=price)

UPDATE users set balance = balance - price

INSERT token_transactions (balance_before/balance_after)

INSERT idempotency_keys (если передан ключ)

COMMIT

11.2 Идемпотентность

canonical JSON: сортировка ключей, одинаковое представление списков.

request_hash хранить в idempotency_keys.

На повтор:

если hash совпал → вернуть generation_id

если нет → 409

11.3 Enqueue failure (компенсация)

Если после COMMIT не удалось отправить celery task:

В отдельной транзакции:

отметить generation failed с error_message “enqueue_failed”

вернуть токены обратно (ledger credit + update balance)
Это “сверх ТЗ”, но демонстрирует зрелость.

12) Минимальный набор ручных проверок (QA checklist)

 Открыть /trends на телефоне (эмулятор) — карточки кликабельны, не ломаются.

 Создать тренд в /admin/trends/new с preview upload — появился в каталоге (если active).

 Деактивировать тренд — пропал из каталога (active=true).

 Запустить генерацию:

баланс уменьшается на price_tokens

статус меняется queued→running→done

результат отображается

 Повторить POST /generations с тем же Idempotency-Key — баланс не уменьшается второй раз.

 При недостатке токенов — 402, генерация не создаётся.

 Upload видео/картинки — ассет открывается по url.

 SSE подключение — обновляет статус без ручного refresh.

13) Ограничения/упрощения (разрешённые, но описать в README)

Если нужно ускориться, допускаются такие упрощения (но желательно не делать):

Не делать редактирование трендов (только create + toggle active).

Не делать отправку реальных файлов в LLM (только ссылки на assets).

Не делать полноценные роли пользователей (один user + один admin через API ключи).
Но UI+API+async+billing+idempotency должны остаться.

14) Правила выполнения для Codex (как работать)

Делай маленькие атомарные коммиты с понятными сообщениями (bootstrap/db/api/ui/worker/tests/docs).

После каждой фазы запускай smoke-test:

docker-compose up --build

curl на /health, /trends, /generations

Сначала доведи end-to-end (каталог → генерация → результат), потом улучшай (SSE/история/админка).

Не оставляй “TODO: implement later” в критических местах (billing, idempotency, статусы).

Все настройки — через env, без хардкода секретов.

Выполняй реализацию строго по этому документу, с приоритетом: end-to-end работоспособность + корректность списания токенов + адаптивный UI + docker-compose.