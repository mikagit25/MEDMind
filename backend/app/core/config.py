from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MedMind AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database — no default; must be set in .env
    DATABASE_URL: str

    # Redis — no default; must be set in .env
    REDIS_URL: str

    # JWT — no default; must be set in .env (openssl rand -hex 32)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Anthropic / Claude
    ANTHROPIC_API_KEY: str = ""

    # Google Gemini Flash (free fallback — aistudio.google.com)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Groq (free fallback — console.groq.com, 14400 req/day)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Ollama (primary free AI — local, zero cost, no API key)
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5"

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STUDENT: str = "price_student_monthly"
    STRIPE_PRICE_PRO: str = "price_pro_monthly"
    STRIPE_PRICE_CLINIC: str = "price_clinic_monthly"
    STRIPE_PRICE_LIFETIME: str = "price_lifetime_once"

    # PubMed
    PUBMED_API_KEY: str = ""
    PUBMED_RATE_LIMIT: int = 3  # req/sec without key, 10/sec with key

    # AI request limits per tier per day (None = unlimited)
    AI_LIMIT_FREE: int = 5
    AI_LIMIT_STUDENT: int = 50
    AI_LIMIT_PRO: Optional[int] = None
    AI_LIMIT_CLINIC: Optional[int] = None
    AI_LIMIT_LIFETIME: Optional[int] = None

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "MedMind AI <noreply@medmind.ai>"
    FRONTEND_URL: str = "http://localhost:3000"

    # Email encryption (Fernet/AES-256) — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""   # Required in production for email encryption

    # Modules import path
    MODULES_DIR: str = "/app/data/modules"

    # Redis TTL (seconds)
    AI_CACHE_TTL: int = 86400       # 24 hours
    PUBMED_CACHE_TTL: int = 604800  # 7 days

    # Docs (disable in production by default)
    ENABLE_DOCS: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def model_post_init(self, __context) -> None:
        """Validate critical settings at startup."""
        if self.ENVIRONMENT == "production":
            if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 chars in production")
            if not self.ANTHROPIC_API_KEY and not self.GEMINI_API_KEY and not self.GROQ_API_KEY:
                raise ValueError("At least one AI API key must be set in production")


settings = Settings()
