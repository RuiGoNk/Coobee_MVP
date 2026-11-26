# CooBee — инструкция для команды

Для двух разрабов (frontend/backend), ML-инженера  и разработчика Санты. Цель — работать в одном репозитории, не ломать `master`, не терять код.

---

## 1. Репозиторий

`https://github.com/RuiGoNk/Coobee_MVP`

Ветки:
- `master` — **стабильный MVP**, защищён. Прямой push запрещён (только PR).
- `feature/backend` — backend-разраб.
- `feature/frontend` — frontend-разраб.
- `feature/ml` — ML.
- `feature/santa-mvp` — разраб Санты.

**Правило:** каждый работает **только в своей ветке**, в `master` — через Pull Request.

---

## 2. Первый запуск (клонирование)

```bash
git clone https://github.com/RuiGoNk/Coobee_MVP.git
cd Coobee_MVP
git checkout feature/<твоя-зона>
```

**`.env` — не в git.** Создай свой:
```bash
cp .env.example .env
```
Заполни:
- `SECRET_KEY` — `openssl rand -hex 32` (или `-join ((1..64) | % { '{0:x}' -f (Get-Random -Max 16) })` в PowerShell),
- `ADMIN_TOKEN` — то же,
- `TELEGRAM_BOT_TOKEN` — **получи у тимлида защищённым каналом** (не в чат/GitHub).

**Токены/секреты — только защищённым каналом** (личка, менеджер паролей). Не в чат, не в git, не в скриншоты.

---

## 3. Запуск локально

```bash
docker compose up -d
```

Сервисы: `backend`, `db`, `nginx`, `redis`, `bot`, `celery_worker`, `celery_beat`.

Проверка:
```bash
docker compose ps          # все Up/healthy
curl http://localhost/api/v1/healthz   # {"status":"ok"}
```

Миграции (если нужно):
```bash
docker compose exec backend alembic upgrade head
```

Фронт (dev):
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

---

## 4. Workflow с git (важно)

### 4.1. Начало работы
```bash
git checkout feature/<твоя-зона>
git pull origin master          # подтянуть свежий master в свою ветку
```

### 4.2. Правки
- Работай, коммить **осмысленно**:
  ```bash
  git add <файлы>
  git commit -m "feat: <что сделал>"   # feat / fix / docs / chore
  ```

### 4.3. Push в свою ветку
```bash
git push origin feature/<твоя-зона>
```

### 4.4. Pull Request в `master`
1. GitHub → **Pull requests** → **New pull request**.
2. **base: `master`** ← **compare: `feature/<твоя-зона>`**.
3. Заголовок: что сделано. Описание: что, зачем, как проверить.
4. **Create pull request**.
5. Ревью (тимлид / Шустова) → **Merge** (squash или merge — по договорённости).

### 4.5. После merge
```bash
git checkout master
git pull origin master          # обновить master
git checkout feature/<твоя-зона>
git merge master                # влить свежий master в свою ветку
```

**Не пушить в `master` напрямую** — защита отклонит (для не-владельцев). Всё через PR.

---

## 5. Правила коммитов

- **Формат:** `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- **Один коммит — одна логическая правка.** Не мешай фичу и рефакторинг.
- **Не коммить:**
  - `.env`, `node_modules/`, `frontend/dist/`, `__pycache__/`, `.idea/`, `docker-compose.override.yml*`, `static/uploads/`.
  - Если случайно добавил — `git reset HEAD <файл>` (убрать из индекса), потом в `.gitignore`.

---

## 6. Что где (карта репозитория)

```
backend/
  app/
    api/v1/       — эндпоинты (auth, profile, recipients, recommend, feedback, wishlist, feed, admin_catalog)
    core/         — config, security (JWT/HMAC), age, tags (словарь тегов)
    models/       — SQLAlchemy (user, recipient, catalog, feedback, auth_session)
    schemas/      — Pydantic (catalog)
    services/     — ml_service (заглушка ML)
    db/           — base, session
    tasks.py      — Celery-задачи (Gift Calendar, Weekly Drop)
    celery_app.py — Celery + расписание
    bot.py        — aiogram (A2-логин)
  alembic/        — миграции
  tests/          — pytest (test_telegram_auth)
frontend/
  src/
    api.ts        — клиент API
    types.ts      — типы
    icons.tsx     — SVG-иконки
    App.tsx       — роутинг по состоянию, онбординг, форма получателя
    Carousel.tsx  — Tinder/Instagram, сетка 3+2
    CardTinder.tsx, CardInstagram.tsx, ItemDetail.tsx
    RecipientProfile.tsx, MyProfile.tsx, Tabs.tsx
docs/
  README.md       — техническая документация (архитектура, API, ML-контракт)
  TASKS.md        — задачи по зонам
  CUSTOMER_GUIDE.md — взаимодействие с заказчиком
  TEAM_WORKFLOW.md  — этот файл
  backlog.md      — Санта/группы (спринт 5+)
```

Подробности API и ML-контракта — в `docs/README.md`.

---

## 7. ML-контракт 

`get_recommendations(user_profile: dict, recipient_profile: dict) -> list[str]` — ровно 5 `external_id`.
- `user_profile` / `recipient_profile` — словари (см. `docs/README.md`, раздел 7).
- `why` — строка-объяснение «почему подходит этому получателю».
- `tags`/`interests` — только из `app/core/tags.py`.
- Разметка каталога — `catalog.details` (`badges`, `marketplaces`, `rating`, `stock`, …).

**Точка замены:** `backend/app/api/v1/recommend.py`, блок `picked = _fallback_recommend(...)`.

---

## 8. Запрещено / Осторожно

- **Не коммитить секреты** (`.env`, токены, ключи). Утёк токен — **перевыпустить** (@BotFather /revoke).
- **Не пушить в `master`** напрямую.
- **Не force push** в общие ветки (`master`, чужие `feature/*`).
- **Не менять миграции**, которые уже применены (создавай новые).
- **Не ломать сборку** (`npm run build`, `docker compose up` должны проходить).

---

## 9. Если что-то сломалось

1. **Не паниковать, не force push.**
2. Прислать ошибку в чат команды (текст, не скрин) + что делал.
3. Если сломал `master` — сообщить тимлиду, откатить **через revert-PR** (не force push).

---

## 10. Контакты / роли

- **Тимлид / backend-лид:** Шустова — архитектура, ревью, деплой.
- **Frontend:** <имя> — `feature/frontend`.
- **Backend:** <имя> — `feature/backend`.
- **ML:** Ника — `feature/ml`.
- **Санта:** <имя> — `feature/santa-mvp`.
- **ПМ / заказчик:** Белова — приёмка, тексты, пользователи.