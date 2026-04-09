# MedMind AI — Medical Education Platform

AI-powered learning platform for medical professionals and veterinarians.  
Built with FastAPI, Next.js 14, React Native (Expo), Claude API.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11, PostgreSQL 15 + pgvector, Redis 7 |
| Frontend | Next.js 14 App Router, TailwindCSS, Zustand |
| Mobile | React Native Expo + WatermelonDB (offline) |
| AI | Anthropic Claude Sonnet/Haiku, Gemini Flash, Groq Llama (fallbacks) |
| Auth | JWT + bcrypt + Google OAuth2, Fernet email encryption (GDPR) |

---

## Development Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 1. Start infrastructure
```bash
docker compose up -d          # PostgreSQL + Redis
```

### 2. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in ANTHROPIC_API_KEY at minimum
alembic upgrade head          # run DB migrations
python -m app.scripts.import_modules   # import 70+ content modules
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 3. Frontend
```bash
cd frontend
npm install
# create frontend/.env.local with: NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev                   # http://localhost:3000
```

### 4. Mobile (optional)
```bash
cd mobile
npm install
npx expo start                # scan QR with Expo Go app
```

### Makefile shortcuts
```bash
make setup          # docker + migrate + import modules
make dev-backend    # start FastAPI dev server
make dev-frontend   # start Next.js dev server
```

---

## Production Deployment

### Requirements
- VPS with Docker & Docker Compose
- Domain pointing to server
- TLS certificates (Let's Encrypt)

### Steps

```bash
# 1. Clone the repo on the server
git clone https://github.com/your-org/medmind.git /opt/medmind
cd /opt/medmind

# 2. Configure environment
cp backend/.env.example backend/.env.prod
# Fill in: ANTHROPIC_API_KEY, POSTGRES_*, REDIS_PASSWORD, JWT_SECRET_KEY,
#           STRIPE_*, SMTP_*, ENCRYPTION_KEY, GOOGLE_CLIENT_*

# 3. Get TLS certificates
certbot certonly --standalone -d medmind.ai -d www.medmind.ai

# 4. Start everything
docker compose -f docker-compose.prod.yml up -d --build

# 5. Import content modules
docker compose -f docker-compose.prod.yml exec backend \
  python -m app.scripts.import_modules
```

### GitHub Actions CI/CD

The workflow at `.github/workflows/ci.yml` runs on every push:
1. **Backend**: ruff lint + pytest (57 tests, SQLite in-memory)
2. **Frontend**: tsc + next build
3. **Deploy** (main branch only): SSH deploy to production server

Required GitHub Secrets:
- `DEPLOY_HOST` — server IP/hostname
- `DEPLOY_USER` — SSH user
- `DEPLOY_SSH_KEY` — private SSH key

---

## Environment Variables

All required variables are documented in [backend/.env.example](backend/.env.example).

Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Claude API key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `JWT_SECRET_KEY` | 256-bit random secret | Yes |
| `ENCRYPTION_KEY` | Fernet key for email encryption | Prod only |
| `STRIPE_SECRET_KEY` | Stripe payments | Optional |
| `SMTP_USER` | Email sending | Optional |
| `GOOGLE_CLIENT_ID` | OAuth2 login | Optional |

---

## Running Tests

```bash
cd backend
./venv/bin/python -m pytest tests/ -v --tb=short
# 57 tests covering: auth, SM-2, security, rate limiting, RBAC, GDPR, import
```

---

## Subscription Tiers

| Tier | AI Requests/Day | Content Access |
|------|----------------|----------------|
| free | 5 | BASE-* modules only |
| student | 50 | All medical modules |
| pro | Unlimited | All + vet + drug database + PubMed |
| clinic | Unlimited | Pro + team features |
| lifetime | Unlimited | Everything forever |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/routes/    # auth, content, progress, ai, admin, compliance, …
│   │   ├── core/             # config, database, security, audit, encryption
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # ai_router, scheduler, notifications, drugs, pubmed
│   │   ├── prompts/          # Claude prompt templates
│   │   └── scripts/          # import_modules.py
│   ├── tests/                # 57 pytest tests
│   ├── alembic/              # DB migrations
│   └── requirements.txt
├── frontend/
│   ├── app/(app)/            # Protected pages (Next.js App Router)
│   ├── components/           # UI components + layout
│   └── lib/                  # API client, Zustand auth store
├── mobile/
│   ├── app/(tabs)/           # Tab screens (dashboard, flashcards, ai, …)
│   └── src/lib/              # API client, WatermelonDB, notifications, offline AI
├── Modules/                  # JSON content modules (70+)
├── docs/                     # TASKS_V2.md (progress tracker), DB schema, prompts
├── docker-compose.yml        # Development
├── docker-compose.prod.yml   # Production (with nginx)
└── nginx.conf                # Nginx reverse proxy config
```

---

## Architecture Notes

- **AI routing**: Claude Sonnet for complex queries, Haiku for simple; falls back to Gemini → Groq → Ollama if keys unavailable
- **GDPR**: Email fields encrypted with Fernet; HMAC hash for login lookup; data export (Art. 20) and anonymised deletion (Art. 17)
- **Offline mobile**: WatermelonDB SQLite for flashcard data; keyword-based AI stub when offline; queue for retry when reconnected
- **SM-2**: Standard Leitner-style spaced repetition; interval and ease factor stored per card per user
- **Push notifications**: Expo push token registered on login; daily 9 AM local reminder scheduled based on due card count
