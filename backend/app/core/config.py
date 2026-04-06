from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MedMind AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://medmind:medmind_secret@localhost:5432/medmind"

    # Redis
    REDIS_URL: str = "redis://:medmind_redis_secret@localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Anthropic / Claude
    ANTHROPIC_API_KEY: str = ""

    # Google Gemini Flash (free fallback #2 — aistudio.google.com)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Groq (free fallback #3 — console.groq.com, 14400 req/day)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Ollama (PRIMARY free AI — local, zero cost, no API key)
    # Recommended: qwen2.5 (multilingual, medical), llama3.2, deepseek-r1, mistral
    # Setup: brew install ollama && ollama pull qwen2.5 && ollama serve
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5"

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # PubMed
    PUBMED_API_KEY: str = ""
    PUBMED_RATE_LIMIT: int = 3  # requests/sec without key, 10/sec with key

    # AI Request limits per tier per day
    AI_LIMIT_FREE: int = 5
    AI_LIMIT_STUDENT: int = 50
    AI_LIMIT_PRO: int = 999999
    AI_LIMIT_CLINIC: int = 999999
    AI_LIMIT_LIFETIME: int = 999999

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "MedMind AI <noreply@medmind.ai>"
    FRONTEND_URL: str = "http://localhost:3000"

    # Modules import path
    MODULES_DIR: str = "/app/data/modules"

    # Redis TTL (seconds)
    AI_CACHE_TTL: int = 86400       # 24 hours
    PUBMED_CACHE_TTL: int = 604800  # 7 days

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
