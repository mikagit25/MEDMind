# MedMind AI — Medical Education Platform

AI-powered learning platform for medical professionals and veterinarians.

## Stack
- **Backend**: FastAPI + Python 3.11, PostgreSQL 15 + pgvector, Redis 7, Alembic
- **Frontend**: Next.js 14 App Router + TailwindCSS + Zustand
- **AI**: Anthropic Claude (Haiku for simple, Sonnet for complex)

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### 2. Start Infrastructure
```bash
docker compose up -d
```

### 3. Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env       # fill in ANTHROPIC_API_KEY
alembic upgrade head        # run migrations
python -m app.scripts.import_modules   # import 70 modules
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend Setup
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                 # runs on http://localhost:3000
```

Or use the Makefile:
```bash
make setup          # docker + migrate + import
make dev-backend    # start API server
make dev-frontend   # start Next.js dev server
```

## API Documentation
After starting the backend, visit: http://localhost:8000/docs

## Module Structure
JSON modules are in `Modules/`. Import script reads all `module_*.json` files.

## Subscription Tiers
| Tier | Content Access |
|------|----------------|
| free | Fundamental modules (BASE-*) only |
| student | All medical modules |
| pro | All modules + vet content + drug database |
| clinic | Pro + team features |
| lifetime | Unlimited forever |

## Project Structure
```
├── backend/           FastAPI application
│   ├── app/
│   │   ├── api/       Route handlers
│   │   ├── core/      Config, DB, security
│   │   ├── models/    SQLAlchemy models
│   │   ├── schemas/   Pydantic schemas
│   │   ├── services/  AI router, PubMed
│   │   └── scripts/   Module importer
│   ├── alembic/       Database migrations
│   └── requirements.txt
├── frontend/          Next.js application
│   ├── app/           Pages (App Router)
│   ├── components/    Reusable components
│   └── lib/           API client, Zustand store
├── Modules/           JSON content modules (70+)
├── docs/              Development docs
└── docker-compose.yml
```
