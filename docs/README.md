# CooBee MVP — техническая документация

Версия: MVP (недели 1–4 + доработки). Стек: FastAPI, PostgreSQL, React (Vite + TS + Tailwind), Celery + Redis, aiogram, nginx, Docker.

---

## 1. Архитектура

```
[Telegram Bot] <── aiogram ──┐
                            │
[React SPA] ── /api/v1 ──> [nginx] ──> [FastAPI backend] ──> [PostgreSQL]
                                │              │
                                │              └──> [Redis] <──> [Celery worker + beat]
                                └── /static, / (dist)
```

Сервисы (`docker-compose.yml`): `backend`, `db`, `nginx`, `redis`, `bot`, `celery_worker`, `celery_beat`.

- **backend** — FastAPI, все API, JWT, админка каталога.
- **db** — PostgreSQL 15.
- **nginx** — отдаёт фронт (`frontend/dist`), `/static/`, проксирует `/api/` на backend.
- **redis** — брокер Celery.
- **bot** — aiogram, обрабатывает `/start auth_<id>` (A2-логин) и шлёт напоминания.
- **celery_worker / celery_beat** — фоновые задачи (Gift Calendar, Weekly Drop).

---

## 2. Переменные окружения (`.env`)

| Переменная | Назначение |
|---|---|
| `SECRET_KEY` | подпись JWT (HS256) |
| `ADMIN_TOKEN` | токен админ-эндпоинтов (`X-Admin-Token`) |
| `JWT_EXPIRE_DAYS` | срок JWT (30) |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `TELEGRAM_BOT_TOKEN` | токен бота |
| `TELEGRAM_BOT_USERNAME` | `Coobee_Ai_bot` (для deep link) |
| `REDIS_URL` | `redis://redis:6379/0` |

Секреты **только** в `.env` (в git не коммитится, есть `.env.example`).

---

## 3. Авторизация

### 3.1. A1 — Telegram Login Widget (десктоп)
`POST /api/v1/auth/telegram`
Тело: поля виджета (`id`, `first_name`, `username`, `auth_date`, `hash`, …).
Проверка: HMAC-SHA256 от `data_check_string` с ключом `SHA256(bot_token)`, TTL `auth_date` (24ч).
Ответ: `{ access_token, token_type: "bearer", user_id }`.

### 3.2. A2 — deep link через бота (мобильный, основной)
1. `POST /api/v1/auth/session` → `{ session_id, deep_link, expires_at }`.
2. Фронт показывает кнопку «Открыть Telegram» (`deep_link` = `https://t.me/<bot>?start=auth_<session_id>`).
3. Бот ловит `/start auth_<id>`, помечает сессию `confirmed`, привязывает `user_id`.
4. Фронт поллит `GET /api/v1/auth/session/<id>` (каждые 2 сек):
   - `pending` — ждём;
   - `confirmed` + `access_token` — сохраняем JWT;
   - `expired` — сессия истекла (TTL 10 мин).

### 3.3. JWT и защита
- JWT (HS256, 30 дней), хранится в `localStorage` (`coobee_jwt`).
- Защищённые эндпоинты: заголовок `Authorization: Bearer <jwt>`.
- Dependency `get_current_user` (`app/core/security.py`) — проверяет JWT, достаёт `User`.
- При истечении — `401` (авто-логаут пока не реализован, в бэклоге).

### 3.4. Пользователь
`users`: `id UUID`, `telegram_id BIGINT unique`, `username`, `created_at`.
Создаётся при первом входе (A1 или A2).

---

## 4. Профиль дарителя (`user_profiles`)

Поля: `birth_date` **или** `birth_year` (CHECK: хотя бы одно), `gender`, `occupation`, `interests JSONB`, `style JSONB`, `budget_range`, `city`.

- `GET /api/v1/profile/me` — профиль или `null`.
- `PUT /api/v1/profile/me` — upsert. Валидация: нужен `birth_date` или `birth_year`.

**Правило возраста:** если есть `birth_date` — точный возраст; если `birth_year` — `current_year - birth_year` (пересчитывается). `age_group` (0-3 … 56+) — **производная**, вычисляется на лету (`app/core/age.py`), в БД не хранится.

---

## 5. Получатели (`recipients`)

Поля: `name`, `relationship`, `gender`, `birth_date` **или** `age` (CHECK), `age_updated_at`, `occasion`, `relationship_level`, `budget_range`, `details JSONB`, `notifications_enabled`, `is_deleted`.

`details` — гибкая анкета (блок 3 из ТЗ): `interests[]`, `style[]`, `occupation`, `family_status`, `children_ages[]`, `pets[]`, `delivery_city`, `delivery_district`, `paired_gift_ok`, `celebration_date`.

API:
- `GET /api/v1/recipients` — список (без `is_deleted`).
- `POST /api/v1/recipients` — создать.
- `PUT /api/v1/recipients/{id}` — обновить.
- `DELETE /api/v1/recipients/{id}` — soft-delete (`is_deleted=true`).
- `GET /api/v1/recipients/{id}/likes` — история лайков (полный товар + `why` из снимка).

**Правило возраста получателя:** `birth_date` (если знаем) → точный возраст + календарь ДР. `age` (если дату не знаем) → «замерзает», есть `age_updated_at` для напоминания уточнить.

---

## 6. Каталог (`catalog`)

Поля: `external_id` (бизнес-ключ, `item_001`; **по нему работает ML**), `title`, `description`, `price_min/max`, `tags JSONB`, `image_url`, `marketplace_url`, `is_available`, `is_paired`, `delivery_type` (`physical`/`digital`/`certificate`), `delivery_regions JSONB`, `details JSONB`, `created_at`.

`details` (заполняет Ника/админ): `brand`, `model`, `category`, `rating`, `reviews_count`, `stock`, `delivery_days`, `occasions[]`, `recipient_types[]`, `gender_affinity`, `professions[]`, `age_groups[]`, `kid_age_groups[]`, `relationship_level[]`, `family_status[]`, `pet_tags[]`, `style[]`, `city_scope`, `source_ref`, **`marketplaces[]`** (`[{name, url}]`), **`badges[]`** (`[{code, label}]`).

**Админка** (заголовок `X-Admin-Token`):
- `POST /api/v1/admin/catalog` — создать товар.
- `POST /api/v1/admin/catalog/batch` — batch (JSON-массив).
- `POST /api/v1/admin/catalog/{id}/image` — загрузка фото (jpg/png/webp, сигнатура проверяется).
- `GET /api/v1/admin/catalog` — список.

---

## 7. Рекомендации (`POST /api/v1/recommend`)

Вход: `{ recipient_id }` (JWT обязателен).
Логика:
1. Достаём получателя и профиль дарителя.
2. **Исключаем** уже оценённые для этого получателя: `like` + `dislike` + `have` (`feedback`).
3. Вызываем ML (сейчас **заглушка** `_fallback_recommend`: ранжирование по тегам/бюджету; **точка замены** — `app/api/v1/recommend.py`).
4. Отдаём 5 товаров: `external_id`, `title`, `description`, `price_*`, `image_url`, `marketplace_url`, `marketplaces`, `badges`, **`why`**.

**`why`** — объяснение «почему подходит **этому** получателю», генерирует ML (сейчас заглушка: «совпадает по интересам: …; в бюджете …»). Это **свойство пары товар+получатель**, не товара.

**Контракт с ML (Ника):**
```python
get_recommendations(user_profile: dict, recipient_profile: dict) -> list[str]  # ровно 5 external_id
```
Профили — словари (см. `_profile_to_dict`, `_recipient_to_dict`). Бэкенд сам достаёт карточки по `external_id`. Если ML вернёт не 5 или упадёт — fallback.

**Точка замены:** в `recommend.py` блок `picked = _fallback_recommend(...)` заменить на вызов ML + добавить `why` из ответа ML (если Ника отдаёт объяснение — подставить в `RecommendItem.why`).

---

## 8. Обратная связь (`feedback`)

Модель: `user_id`, `item_id`, `recipient_id` (nullable), `action` (`like`/`dislike`/`have`), `context` (`recipient`/`self_wishlist`), `meta JSONB` (снимок `why` для лайка), `created_at`.

Уникальность (частичные индексы):
- `(user_id, item_id, recipient_id) WHERE context='recipient'`
- `(user_id, item_id) WHERE context='self_wishlist'`

API:
- `POST /api/v1/feedback` — **upsert** (одна запись на товар+контекст; `action` меняется). Для `like` передаётся `why` (снимок из подборки) → в `meta`.
- `DELETE /api/v1/feedback/{external_id}?context=...&recipient_id=...` — снять оценку.

Правила:
- `like` для получателя → история лайков, товар уходит из подборки.
- `dislike`/`have` → товар **никогда** больше не в подборке этого получателя.
- Лайк в «Для себя» (`self_wishlist`) → авто-вишлист.

---

## 9. Вишлист и лента «Для себя»

- `GET /api/v1/wishlist` — товары с `like` + `context=self_wishlist`.
- `POST /api/v1/wishlist/{external_id}` — добавить (upsert like self_wishlist).
- `DELETE /api/v1/wishlist/{external_id}` — убрать.
- `GET /api/v1/feed` — 30 товаров «для себя»: исключает вишлист-лайки и `have` пользователя, ранжирует по интересам профиля.

---

## 10. Фоновые задачи (Celery)

`app/celery_app.py` — расписание (`Europe/Moscow`):
- **Gift Calendar** — ежедневно 10:00. Для каждого получателя с `notifications_enabled=true`: ДР (за 14 дней, только если `birth_date`), Новый год, 8 марта (female/unisex), 23 февраля (male/unisex). Шлёт в Telegram: «У «<имя>» скоро <повод>. Начать подбор? → <APP_DOMAIN>».
- **Weekly Drop** — четверг 10:00. Для каждого пользователя: 5 товаров по лайкам/интересам → сообщение в Telegram.

`app/tasks.py`: `_gift_calendar()`, `_weekly_drop()` — async-логика; обёртки `gift_calendar()`, `weekly_drop()` — celery-таски. Отправка — `_send()` (создаёт `Bot` на вызов, закрывает сессию).

**Запуск вручную для отладки:**
```bash
docker compose exec celery_worker python -c "import asyncio; from app.tasks import _gift_calendar; asyncio.run(_gift_calendar())"
```

---

## 11. Фронтенд (React + Vite + TS + Tailwind)

Структура `frontend/src/`:
- `api.ts` — клиент API (все методы, JWT в заголовке).
- `types.ts` — общие типы (`RecommendItem`, `FeedbackAction`, `Badge`, `Marketplace`).
- `icons.tsx` — SVG-иконки (Heart, ThumbDown, CheckCircle, ChevronRight).
- `App.tsx` — роутинг по состоянию (логин → онбординг → вкладки), `RecipientForm`, `Onboarding`.
- `Carousel.tsx` — переключатель Tinder/Instagram, сетка 3+2 на десктопе, оценка/навигация.
- `CardTinder.tsx`, `CardInstagram.tsx` — карточки.
- `ItemDetail.tsx` — детальная (цена, описание, `why`, маркетплейсы, «в вишлист», оценки).
- `RecipientProfile.tsx` — профиль получателя (просмотр, редактирование, история лайков).
- `MyProfile.tsx` — профиль дарителя (просмотр/редактирование).
- `Tabs.tsx` — «Для себя» / «Вишлист».

Сборка: `npm run build` → `frontend/dist`, nginx отдаёт его. Для dev: `npm run dev` (`:5173`, прокси `/api`).

**Правила карточки:**
- Короткая: фото, название, иконки-оверлеи (контур → заливка при выборе), badges (если есть). **Без цены/«Купить».**
- Детальная: цена, описание, `why` (**только если есть**), маркетплейсы, «в вишлист», оценки.

**Оценка vs навигация:** тап по иконке = оценка (не листает); стрелка `>`/свайп = переход (не оценка); повторный тап по той же иконке = снять оценку.

---

## 12. Точки расширения (для Санты и групповых комнат)

См. `docs/backlog.md`. Заложено:
- `POST /api/v1/groups`, `/rooms` — заглушки `501` (контракт виден).
- `recommend` принимает `recipient_id`; для Санты нужен режим «по профилю без получателя» (`profile_override` + `budget_override`) — **TODO**.
- `feedback.context` расширяем (`santa`, `room`) — новые контексты.
- `user_profiles` — источник анкеты для Санты (участник = получатель).

**Важно:** денег не собираем — только подбор, голосование, ссылки на покупку.

---

## 13. ML-инженеру (Ника) — что нужно

1. Реализовать `get_recommendations(user_profile, recipient_profile) -> list[str]` (ровно 5 `external_id`).
2. Заполнять `catalog.details` при разметке: `badges`, `marketplaces`, `rating`, `stock`, `occasions`, `age_groups`, `style`, `pet_tags` и т.д.
3. Генерировать **`why`** для пары товар+получатель (объяснение «почему подходит»). Формат — строка.
4. Соблюдать словарь тегов (`app/core/tags.py`): `interests`/`tags` — из `HOBBY`/`STYLE`, иначе ML мажет.

**Контракт ID:** ML возвращает `external_id` (`item_001`), бэкенд достаёт карточку по нему.

---

## 14. DevOps — деплой

**Локально:** `docker compose up -d`, фронт — `npm run build` + `docker compose restart nginx`.

**Прод (VPS):** Docker + Compose, `.env` с прод-секретами, домен + HTTPS (Let's Encrypt в nginx), убрать `--reload` (у нас его нет), `ports` для db наружу не публиковать.

**Тоннель (тест):** `cloudflared tunnel --url http://localhost:80 --protocol http2` (QUIC режется VPN). URL одноразовый, живёт пока процесс.

**Миграции:** Alembic (`alembic upgrade head`). Файлы миграций — в `backend/alembic/versions/` (volume).

**Важно:** после `docker compose up -d --build backend` иногда нужен `docker compose restart nginx` (кеш IP старого контейнера).

---

## 15. Известные ограничения MVP

- JWT 30 дней, без refresh/авто-логаута.
- ML — заглушка (ранжирование по тегам/бюджету).
- `why` — заглушка (по тегам/бюджету).
- Название в Tinder-карточке иногда не отображается (слои/кеш, в бэклоге).
- Группы/Санта — заглушки `501`.
- Платежей нет (по дизайну).