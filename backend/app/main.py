"""FastAPI application entry point."""
from contextlib import asynccontextmanager
import logging
from pathlib import Path

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings

# Initialize Sentry before the app starts (no-op if DSN is empty)
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=f"medmind-backend@{settings.VERSION}",
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        # Don't send PII by default
        send_default_pii=False,
    )
from app.core.database import engine, Base
from app.core.redis_client import get_redis, close_redis
from app.api.v1.routes import auth, content, progress, ai, payments, notes, bookmarks, achievements, admin, courses, veterinary, compliance, dashboard, notifications, memory, lessons, imaging, user_flashcards
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MedMind AI backend...")

    # Auto-create tables from models (dev mode — skips alembic)

    # Step 1: Try extensions in separate autocommit connections so a failure
    # doesn't abort the main transaction (pgvector not available on PG 9.6)
    for ext in ("vector", "pg_trgm", "uuid-ossp"):
        try:
            async with engine.connect() as conn:
                await conn.execution_options(isolation_level="AUTOCOMMIT")
                await conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{ext}"'))
        except Exception as e:
            logger.debug("Extension %s not available: %s", ext, e)

    # Step 2: Create tables + seed in one transaction
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Seed specialties if empty
        result = await conn.execute(text("SELECT COUNT(*) FROM specialties"))
        count = result.scalar()
        if count == 0:
            import uuid as _uuid
            specialties = [
                ("cardiology", "Cardiology"),
                ("neurology", "Neurology"),
                ("surgery", "Surgery"),
                ("obstetrics", "Obstetrics & Gynecology"),
                ("pediatrics", "Pediatrics"),
                ("therapy", "Internal Medicine"),
                ("pharmacology", "Pharmacology"),
                ("lab_diagnostics", "Laboratory Diagnostics"),
                ("respiratory", "Respiratory Medicine"),
                ("veterinary", "Veterinary"),
            ]
            for code, name in specialties:
                await conn.execute(text(
                    "INSERT INTO specialties (id, code, name, is_active, is_veterinary) "
                    "VALUES (:id, :code, :name, true, false) "
                    "ON CONFLICT (code) DO UPDATE SET is_active=true"
                ), {"id": str(_uuid.uuid4()), "code": code, "name": name})
            logger.info("Seeded %d specialties", len(specialties))

    # Seed imaging library (opens its own session after tables are created)
    try:
        from scripts.seed_imaging import seed as seed_imaging
        await seed_imaging()
        logger.info("Medical imaging library seeded.")
    except Exception as e:
        logger.warning("Imaging seed failed (non-fatal): %s", e)

    await get_redis()  # Initialize Redis connection
    start_scheduler()  # registers jobs AND starts APScheduler
    logger.info("MedMind backend ready! Scheduler started.")
    yield
    # Shutdown
    logger.info("Shutting down...")
    stop_scheduler()
    await close_redis()


app = FastAPI(
    title="MedMind AI API",
    description="Medical & Veterinary Education Platform API",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if (settings.DEBUG or settings.ENABLE_DOCS) else None,
    redoc_url="/redoc" if (settings.DEBUG or settings.ENABLE_DOCS) else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
# lessons must be registered before content to take precedence on GET /lessons/{id}
app.include_router(lessons.router, prefix=API_PREFIX)
app.include_router(content.router, prefix=API_PREFIX)
app.include_router(progress.router, prefix=API_PREFIX)
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(notes.router, prefix=API_PREFIX)
app.include_router(bookmarks.router, prefix=API_PREFIX)
app.include_router(achievements.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(courses.router, prefix=API_PREFIX)
app.include_router(veterinary.router, prefix=API_PREFIX)
app.include_router(compliance.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(memory.router, prefix=API_PREFIX)
app.include_router(imaging.router, prefix=API_PREFIX)
app.include_router(user_flashcards.router, prefix=API_PREFIX)

# Serve uploaded media files (images for lessons).
# In production MEDIA_ROOT=/app/data/media; locally it falls back to ./data/media.
_media_dir = Path(settings.MEDIA_ROOT)
try:
    _media_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    # Fallback for dev/CI environments where /app is read-only
    _media_dir = Path("./data/media")
    _media_dir.mkdir(parents=True, exist_ok=True)
app.mount(settings.MEDIA_URL, StaticFiles(directory=str(_media_dir)), name="media")


@app.get("/health")
async def health_check():
    """Basic liveness probe — always fast, never checks dependencies."""
    return {"status": "ok", "version": settings.VERSION, "env": settings.ENVIRONMENT}


@app.get("/readiness")
async def readiness_check():
    """Readiness probe — verifies DB and Redis are reachable before accepting traffic."""
    from fastapi.responses import JSONResponse
    import asyncio

    checks: dict[str, str] = {}
    healthy = True

    # Check PostgreSQL
    try:
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=3.0)
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"
        healthy = False

    # Check Redis
    try:
        redis = await get_redis()
        await asyncio.wait_for(redis.ping(), timeout=3.0)
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if healthy else "not ready",
            "checks": checks,
            "version": settings.VERSION,
        },
    )


@app.get("/")
async def root():
    return {"message": "MedMind AI API", "docs": "/docs"}
