# MedMind AI — Claude Code Guide

> Этот файл читается автоматически при каждом запуске Claude Code.
> Всегда читай `PROJECT_STATE.md` и `docs/MEDMIND_ROADMAP_V3.md` перед началом работы.

---

## Быстрый старт

> ⚠️ На сервере `/opt/medmind` работает **production**. Команды этого раздела — только для
> локальной разработки. На сервере используй раздел «Production» ниже.

```bash
# Поднять инфраструктуру (PostgreSQL 15 + pgvector + Redis) — ТОЛЬКО локально
docker compose up -d

# Backend (FastAPI, порт 8000)
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (Next.js 14, порт 3000)
cd frontend && npm run dev

# Или всё через Make:
make setup       # DB + миграции + импорт модулей (первый раз)
make dev         # backend + frontend параллельно
```

## Production

> ⚠️ **Всегда с `-f docker-compose.prod.yml`.** Голый `docker compose` берёт dev-файл
> `docker-compose.yml`: он пересоздаёт backend/frontend/postgres/redis в сети `medmind_default`,
> nginx перестаёт их видеть → весь сайт 502 (инцидент 21.11.2026). Плюс dev build args
> (нет `NEXT_PUBLIC_GA_ID`, другой `NEXT_PUBLIC_API_URL`).

```bash
P="docker compose -f /opt/medmind/docker-compose.prod.yml"

# Фронтенд (сборка ~20+ мин — запускать в фоне)
$P build frontend && $P up -d --no-deps frontend && docker exec medmind_nginx nginx -s reload

# Backend (код запечён в образ — restart НЕ подхватывает изменения)
$P build backend && $P up -d --no-deps backend && docker exec medmind_nginx nginx -s reload

# После любого пересоздания контейнеров — обязательно перезагрузить nginx (кэширует IP)
docker exec medmind_nginx nginx -s reload

$P logs -f frontend                                               # логи
$P ps                                                             # статус
```

Проверка после выкладки: `curl -s -o /dev/null -w '%{http_code}' https://medmind.pro/` → 200,
и `docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' medmind_frontend` → `medmind_internal`.

## Тесты

```bash
cd backend && pytest tests/ -v                    # все тесты
cd backend && pytest tests/test_auth.py -v        # конкретный файл
cd backend && pytest tests/ -v -k "patient"       # по ключевому слову
```

## Миграции БД

```bash
cd backend && alembic upgrade head                # применить новые
cd backend && alembic revision --autogenerate -m "description"  # создать новую
```

## Импорт контента

```bash
cd backend && python -m app.scripts.import_modules    # все модули из Modules/
```

---

## Структура проекта

```
/opt/medmind/
├── backend/
│   ├── app/
│   │   ├── main.py              # точка входа FastAPI
│   │   ├── core/                # config.py, security.py, database.py
│   │   ├── models/              # SQLAlchemy модели (User, Lesson, Drug…)
│   │   ├── schemas/             # Pydantic схемы (request/response)
│   │   ├── api/v1/routes/       # роутеры: auth, content, ai, drugs, progress…
│   │   ├── services/            # бизнес-логика: ai_service, email, pubmed…
│   │   ├── prompts/             # системные промпты для AI-режимов
│   │   └── scripts/             # import_modules.py, generate_lay_summaries.py…
│   ├── alembic/migrations/      # версии БД
│   └── tests/                   # pytest тесты
├── frontend/
│   ├── app/                     # Next.js App Router страницы
│   │   ├── (app)/               # аутентифицированные страницы (dashboard, modules…)
│   │   ├── articles/            # публичные статьи (SSR)
│   │   ├── drugs/               # публичная база препаратов (SSR, server components)
│   │   └── news/                # публичные новости (SSR)
│   ├── components/              # React компоненты
│   └── lib/                     # api.ts, i18n.ts, categories.ts…
├── mobile/                      # React Native Expo
├── Modules/                     # JSON-файлы учебных модулей (не редактировать)
├── docs/
│   ├── MEDMIND_ROADMAP_V3.md   # текущий роадмап
│   ├── PG15_MIGRATION.md       # инструкция по миграции на PG 15
│   └── archive/                 # устаревшие документы
├── docker-compose.yml           # dev окружение
├── docker-compose.prod.yml      # prod окружение
├── PROJECT_STATE.md             # текущее состояние проекта (читать первым)
└── CLAUDE.md                    # этот файл
```

---

## Ключевые правила

### Безопасность
- **Никогда не коммитить**: `.env`, `client_secret*.json`, `youtube_token*.json`, `auth_account*.py`
- Groq KEY_1/KEY_2 — только для пользовательского AI тьютора; KEY_3/KEY_4 — только для пайплайна генерации контента
- Медицинский дисклеймер обязателен на всех публичных страницах и в AI-режиме «Пациент»

### Коммиты
- Язык коммитов: английский
- Формат: `feat(scope): description` / `fix(scope): description` / `refactor(scope): ...`
- Для роадмап-фаз: `feat(phase-N): описание`
- Никогда не пушить в main без проверки тестов

### Стек
| Слой | Технология |
|------|------------|
| Backend | FastAPI 0.111 + Python 3.11, async |
| ORM | SQLAlchemy 2.0 async + Alembic |
| DB | PostgreSQL 15 + pgvector (Docker) |
| Cache | Redis 7 (rate limiting, AI cache) |
| AI | Anthropic Claude API (Haiku → Sonnet по сложности) |
| Frontend | Next.js 14 App Router + TailwindCSS |
| Auth | JWT + bcrypt + OAuth2 Google |
| Payments | Stripe subscriptions |
| Mobile | React Native Expo + WatermelonDB |

### Подписки
| Тариф | Цена | AI запросов/день |
|-------|------|-----------------|
| Free | $0 | 5 |
| Student | $15/мес | 50 |
| Pro | $40/мес | безлимит |
| Clinic | $199/мес | 10 юзеров безлимит |

### Существующие AI-режимы (до Phase 2)
- `tutor` — объяснение тем (Sonnet)
- `quiz` — генерация вопросов (Haiku)
- `case` — разбор кейсов (Sonnet)
- `explain` — объяснение концепций (Haiku)
- `patient` — для неспециалистов (Haiku) ← добавляется в Phase 2

---

## Публичные страницы (SEO, без авторизации)

Эти маршруты доступны без логина и индексируются поисковиками:
- `/` — лендинг
- `/articles`, `/articles/[slug]` — медицинские статьи
- `/drugs`, `/drugs/[id]` — база препаратов (SSR, H1 в initial HTML)
- `/news`, `/news/[slug]` — новости
- `/calculators`, `/symptoms`, `/how-it-works`, `/pricing`

После Phase 3 добавятся: `/learn/glossary`, `/learn/topics/[slug]`, `/learn/drugs/[slug]`

---

## Ссылки

- Роадмап: `docs/MEDMIND_ROADMAP_V3.md`
- Состояние проекта: `PROJECT_STATE.md`
- Схема БД: `docs/DB_SCHEMA.sql`
- Ошибки и фиксы: `docs/ERRORS_LOG.md`
- Миграция PG15: `docs/PG15_MIGRATION.md`
