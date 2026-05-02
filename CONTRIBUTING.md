# Contributing to MedMind AI

## Quick start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 15 + pgvector (or use Docker)
- Redis 7 (or use Docker)

### Local setup

```bash
# 1. Clone and enter repo
git clone https://github.com/your-org/medmind.git
cd medmind

# 2. Start dev dependencies (DB + Redis)
docker compose up -d postgres redis

# 3. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in JWT_SECRET_KEY + at least one AI key
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 4. Frontend (new terminal)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

API docs at http://localhost:8000/docs, frontend at http://localhost:3000.

## Project structure

```
medmind/
├── backend/          # FastAPI + SQLAlchemy 2.0 async
│   ├── app/
│   │   ├── api/v1/routes/   # one file per domain
│   │   ├── core/            # config, db, redis, audit
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response
│   │   ├── services/        # business logic (AI router, PDF, SM-2…)
│   │   └── prompts/         # LLM prompt templates
│   ├── alembic/             # DB migrations
│   ├── scripts/             # seed scripts
│   └── tests/               # pytest async tests
├── frontend/         # Next.js 14 App Router + Tailwind
│   ├── app/          # pages (file-based routing)
│   ├── components/   # reusable UI + providers
│   └── lib/          # api client, store, analytics
├── mobile/           # React Native Expo (offline-first)
├── nginx.conf        # production HTTPS reverse proxy
└── docker-compose.prod.yml
```

## Development workflow

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Write code + tests
3. Run backend tests: `cd backend && pytest`
4. Run frontend lint: `cd frontend && npm run lint`
5. Open a pull request targeting `main`

## Backend conventions

- **Routes**: one file per domain in `app/api/v1/routes/`. Keep handlers thin — business logic goes in `app/services/`.
- **Models**: SQLAlchemy 2.0 `async` session everywhere. Add indexes for any column used in `WHERE` or `ORDER BY`.
- **Migrations**: always generate with `alembic revision --autogenerate -m "description"` and review the generated file before committing.
- **Tests**: pytest-asyncio. Use `aiosqlite` in-memory DB for unit tests; never mock the DB for integration tests.
- **Secrets**: never hard-code; use `app/core/config.py` `Settings` class.

## Frontend conventions

- **Pages**: Next.js App Router. Use `"use client"` only when you need browser APIs or hooks.
- **API calls**: always use `lib/api.ts` wrappers, never raw `fetch`.
- **Analytics**: use `lib/analytics.ts` (`trackEvent(...)`) for product events, never log PII.
- **Styles**: Tailwind utility classes. Custom tokens defined in `tailwind.config.js`.

## Security checklist (before every PR)

- [ ] No secrets in code or comments
- [ ] User input validated at API boundary (Pydantic schema)
- [ ] AI input passed through `sanitize_ai_message()`
- [ ] New endpoints require `get_current_user` dependency
- [ ] Admin endpoints require role check

## Running tests

```bash
# Backend
cd backend
pytest -v --tb=short

# Frontend lint
cd frontend
npm run lint
```

## Need help?

Open a GitHub issue or reach out in the team Slack.
