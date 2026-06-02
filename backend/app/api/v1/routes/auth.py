"""Authentication routes."""
from datetime import datetime, timedelta
import hashlib
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, hash_email,
    create_access_token, create_refresh_token,
)
from app.core.config import settings
from app.core.encryption import encrypt_email, decrypt_email, email_search_hash
from app.models.models import User, RefreshToken, UserConsent
from app.core.audit import audit, get_ip, get_ua
from pydantic import BaseModel
from app.schemas.schemas import UserRegister, UserLogin, TokenResponse, RefreshRequest, UserOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

AUTH_RATE_LIMIT = 10   # max failed attempts
AUTH_RATE_WINDOW = 300  # 5-minute sliding window (seconds)


def _client_ip(request: Request) -> str:
    """Get real client IP from X-Forwarded-For (nginx proxy) or direct connection."""
    forwarded = request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP")
    if forwarded:
        # X-Forwarded-For may be comma-separated; take the first (client) IP
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_auth_rate_limit(request: Request) -> None:
    """Block IPs with too many failed auth attempts (Redis-backed, survives restarts)."""
    from app.core.redis_client import get_redis
    ip = _client_ip(request)
    key = f"auth_fails:{ip}"
    redis = await get_redis()
    count = await redis.get(key)
    if count and int(count) >= AUTH_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait 5 minutes.",
        )


async def record_failed_attempt(request: Request) -> None:
    from app.core.redis_client import get_redis
    ip = _client_ip(request)
    key = f"auth_fails:{ip}"
    redis = await get_redis()
    pipe = redis.pipeline()
    await pipe.incr(key)
    await pipe.expire(key, AUTH_RATE_WINDOW)
    await pipe.execute()


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    preferences: Optional[dict] = None


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    await check_auth_rate_limit(request)
    email_lower = data.email.lower()
    search_hash = email_search_hash(email_lower)

    # Check if email already exists (using search hash for encrypted lookup)
    existing = await db.execute(
        select(User).where(User.email_hash == search_hash)
    )
    if existing.scalar_one_or_none():
        await record_failed_attempt(request)
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=encrypt_email(email_lower),
        email_hash=search_hash,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        subscription_tier="free",
    )
    db.add(user)
    try:
        await db.flush()  # get user.id
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")

    # Record GDPR consents
    ip = request.client.host if request.client else None
    for consent_type in ["terms", "privacy"]:
        consent = UserConsent(
            user_id=user.id,
            consent_type=consent_type,
            version="1.0",
            ip_address=ip,
        )
        db.add(consent)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    await db.refresh(user)

    access_token = create_access_token(str(user.id))
    raw_refresh, hashed_refresh = create_refresh_token()

    refresh = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
    await db.commit()

    # Send welcome email (non-blocking) — decrypt email first (stored Fernet-encrypted in DB)
    from app.services.email_service import send_welcome_email
    from app.core.encryption import decrypt_email
    try:
        plain_email = decrypt_email(user.email)
        await send_welcome_email(plain_email, user.first_name or "there")
    except Exception:
        pass  # Never fail registration due to email error

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserOut.model_validate(user),
    )


@router.post("/logout", status_code=200)
async def logout(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Revoke the refresh token, effectively logging the user out."""
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user.id,
        )
    )
    token = result.scalar_one_or_none()
    if token:
        token.is_revoked = True
        await db.commit()
    return {"detail": "Logged out successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    await check_auth_rate_limit(request)
    email_lower = data.email.lower()
    search_hash = email_search_hash(email_lower)
    result = await db.execute(
        select(User).where(User.email_hash == search_hash, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    # Fallback: plain-text email lookup (accounts registered before encryption was enabled)
    if not user:
        result_plain = await db.execute(
            select(User).where(User.email == email_lower, User.is_active == True)
        )
        user = result_plain.scalar_one_or_none()
        if user:
            # Migrate email_hash to current algorithm
            user.email_hash = search_hash
            await db.commit()

    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        await record_failed_attempt(request)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(str(user.id))
    raw_refresh, hashed_refresh = create_refresh_token()

    refresh = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
    await audit(db, "user_login", user_id=user.id, ip_address=get_ip(request), user_agent=get_ua(request))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    refresh = result.scalar_one_or_none()
    if not refresh:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Revoke old token (rotation)
    refresh.is_revoked = True

    # Get user
    user_result = await db.execute(select(User).where(User.id == refresh.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(str(user.id))
    raw_refresh, hashed_refresh = create_refresh_token()

    new_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_refresh)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def get_me(
    user: User = Depends(get_current_user),
):
    return UserOut.model_validate(user)


_ME_ALLOWED_ROLES = {"student", "doctor", "teacher", "nurse", "vet", "vet_student", "other"}


@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.role is not None:
        role = data.role.lower().strip()
        if role in _ME_ALLOWED_ROLES:
            user.role = role
    if data.preferences is not None:
        user.preferences = {**(user.preferences or {}), **data.preferences}
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


ALLOWED_ROLES = {"student", "doctor", "teacher", "nurse", "vet", "vet_student", "other"}

# Maps onboarding UI role values → DB role column values
ONBOARDING_ROLE_MAP = {
    "student":      "student",
    "doctor":       "doctor",
    "teacher":      "teacher",
    "professor":    "teacher",   # legacy onboarding value
    "veterinarian": "vet",
    "vet":          "vet",
    "vet_student":  "vet_student",
    "nurse":        "nurse",
    "other":        "other",
}


@router.post("/onboarding", response_model=UserOut)
async def complete_onboarding(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Save onboarding preferences and mark onboarding complete.

    Critically: the 'role' field updates user.role (DB column),
    not just preferences — this is what grants teacher/doctor access.
    """
    # Map onboarding role → DB role and update the actual role column
    if role_raw := data.get("role"):
        db_role = ONBOARDING_ROLE_MAP.get(str(role_raw).lower(), "student")
        user.role = db_role

    # Store everything else in preferences (goal, specialties, daily_minutes, etc.)
    prefs_data = {k: v for k, v in data.items() if k != "role"}
    user.preferences = {**(user.preferences or {}), **prefs_data}
    user.onboarding_completed = True
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


# ── Veterinary Mode ───────────────────────────────────────────────────────────

ALLOWED_SPECIES = {"canine", "feline", "equine", "bovine", "porcine", "avian", "exotic"}

class VetSettingsRequest(BaseModel):
    vet_mode: bool
    species: List[str] = []

@router.put("/veterinary-settings", response_model=UserOut)
async def update_vet_settings(
    data: VetSettingsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enable/disable veterinary mode and select species."""
    invalid = set(data.species) - ALLOWED_SPECIES
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unknown species: {', '.join(invalid)}")
    user.preferences = {
        **(user.preferences or {}),
        "vet_mode": data.vet_mode,
        "vet_species": data.species,
    }
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


# ── Password reset ────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password", status_code=200)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Send password-reset link. Always returns 200 to prevent email enumeration."""
    await check_auth_rate_limit(request)

    search_hash = email_search_hash(data.email.lower())
    result = await db.execute(
        select(User).where(User.email_hash == search_hash, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user:
        import secrets
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Store hashed token in Redis with 1-hour TTL (keyed by hash for O(1) lookup)
        redis = await get_redis()
        await redis.setex(f"pwd_reset:{token_hash}", 3600, str(user.id))

        # Send reset email (SMTP if configured, else logs to console)
        from app.services.email_service import send_password_reset
        await send_password_reset(data.email.lower(), raw_token)

    return {"detail": "If this email is registered, a reset link has been sent."}


@router.post("/reset-password", status_code=200)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate reset token and update password."""
    import uuid as _uuid
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()

    # Look up token in Redis (one-time use — delete immediately after reading)
    redis = await get_redis()
    redis_key = f"pwd_reset:{token_hash}"
    user_id_str = await redis.getdel(redis_key)

    if not user_id_str:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    try:
        user_id = _uuid.UUID(user_id_str if isinstance(user_id_str, str) else user_id_str.decode())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Validate new password
    if len(data.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    user.password_hash = hash_password(data.new_password)

    # Revoke all existing refresh tokens for security
    await db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user.id)
        .values(is_revoked=True)
    )
    await db.commit()

    return {"detail": "Password updated successfully. Please log in again."}


# ============================================================
# GOOGLE OAUTH2
# ============================================================

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google")
async def google_login():
    """Redirect user to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    import urllib.parse
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback — exchange code for tokens, upsert user, return JWT."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    import httpx
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Exchange code for access token
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange Google code")
        tokens = token_res.json()

        # Get user info from Google
        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get Google user info")
        guser = user_res.json()

    email = guser.get("email", "").lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    google_id = str(guser.get("id", ""))
    first_name = guser.get("given_name", "")
    last_name = guser.get("family_name", "")
    avatar_url = guser.get("picture")

    # Upsert user — search by email_hash first, then plain email fallback
    # (plain fallback needed for accounts registered before email encryption was enabled)
    _search_hash = email_search_hash(email)
    result = await db.execute(select(User).where(User.email_hash == _search_hash))
    user = result.scalar_one_or_none()

    if not user:
        # Fallback: search by plain-text email (accounts registered without ENCRYPTION_KEY)
        result_plain = await db.execute(select(User).where(User.email == email))
        user = result_plain.scalar_one_or_none()
        if user:
            # Migrate email_hash to current algorithm
            user.email_hash = _search_hash
            await db.commit()
            await db.refresh(user)  # refresh after commit to avoid expired-attribute access

    if not user:
        # Truly new user — create account
        user = User(
            email=encrypt_email(email),
            email_hash=_search_hash,
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            oauth_provider="google",
            oauth_id=google_id,
            is_verified=True,
            subscription_tier="free",
        )
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            # Race condition or email already exists with different hash
            result2 = await db.execute(select(User).where(User.email_hash == _search_hash))
            user = result2.scalar_one_or_none()
            if not user:
                result3 = await db.execute(select(User).where(User.email == email))
                user = result3.scalar_one_or_none()
                if user:
                    user.email_hash = _search_hash
                    await db.commit()
                    await db.refresh(user)
            if not user:
                raise HTTPException(status_code=500, detail="Account creation failed, please try again")
        else:
            # GDPR consent (implicit via OAuth)
            db.add(UserConsent(user_id=user.id, consent_type="terms", version="1.0"))
            db.add(UserConsent(user_id=user.id, consent_type="privacy", version="1.0"))
            await db.commit()
        await db.refresh(user)

    # Update OAuth info for all found users (new or existing)
    needs_commit = False
    if not user.oauth_provider:
        user.oauth_provider = "google"
        user.oauth_id = google_id
        needs_commit = True
    if avatar_url and not user.avatar_url:
        user.avatar_url = avatar_url
        needs_commit = True
    if not user.is_verified:
        user.is_verified = True
        needs_commit = True
    if needs_commit:
        await db.commit()
    await db.refresh(user)

    # Issue JWT tokens
    access_token = create_access_token(str(user.id))
    raw_refresh, hashed_refresh = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    await db.commit()

    # Store tokens server-side under a short-lived one-time code (60 sec TTL).
    # Only the opaque code goes in the URL — tokens never appear in browser history.
    import secrets as _secrets
    import json as _json
    from app.core.redis_client import get_redis as _get_redis
    from fastapi.responses import RedirectResponse
    import urllib.parse

    one_time_code = _secrets.token_urlsafe(32)
    redis = await _get_redis()
    await redis.setex(
        f"oauth_code:{one_time_code}",
        60,  # 60 seconds TTL
        _json.dumps({
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "onboarding": not user.onboarding_completed,
        }),
    )

    redirect_url = (
        f"{settings.FRONTEND_URL}/auth/google/success"
        f"?code={urllib.parse.quote(one_time_code)}"
    )
    return RedirectResponse(url=redirect_url)


@router.post("/google/exchange")
async def google_exchange_code(code: str):
    """Exchange one-time OAuth code for JWT tokens.
    Called by frontend immediately after redirect — code expires in 60 seconds.
    """
    import json as _json
    from app.core.redis_client import get_redis as _get_redis

    redis = await _get_redis()
    raw = await redis.get(f"oauth_code:{code}")
    if not raw:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth code")

    # Delete immediately — truly one-time use
    await redis.delete(f"oauth_code:{code}")

    data = _json.loads(raw)
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "onboarding": data["onboarding"],
    }


# ── YouTube OAuth callback ────────────────────────────────────────────────────
# Handles automatic token renewal for YouTube channels.
# Flow: cron generates auth URL → sends to Telegram → admin taps link →
#       Google redirects here with code → token saved automatically.

_YT_TOKEN_PATHS = {
    "en": "/app/youtube_token_en.json",
    "es": "/app/youtube_token_es.json",
}
_YT_SECRET_PATHS = {
    "en": "/app/client_secret_web.json",
    "es": "/app/client_secret_account2_web.json",
}
_YT_CALLBACK_URL = "https://medmind.pro/api/v1/auth/youtube/callback"

@router.get("/youtube/callback")
async def youtube_token_callback(
    code: str | None = None,
    state: str = "en",      # carries account id: "en" or "es"
    error: str | None = None,
):
    """
    Receives YouTube OAuth redirect. Exchanges code for token and saves it.
    account is passed via `state` param so redirect_uri stays clean (no query params).
    """
    import json as _json, time as _time, httpx as _httpx
    from fastapi.responses import HTMLResponse

    account = state  # state carries "en" or "es"

    if error:
        return HTMLResponse(f"<h2>❌ Auth error: {error}</h2>", status_code=400)
    if not code:
        return HTMLResponse("<h2>❌ No code received</h2>", status_code=400)
    if account not in _YT_TOKEN_PATHS:
        return HTMLResponse(f"<h2>❌ Unknown account: {account}</h2>", status_code=400)

    secret_path = _YT_SECRET_PATHS.get(account)
    token_path  = _YT_TOKEN_PATHS[account]

    try:
        with open(secret_path) as f:
            secret = _json.load(f)
        web = secret.get("web") or secret.get("installed") or {}
        client_id     = web["client_id"]
        client_secret = web["client_secret"]
    except Exception as e:
        return HTMLResponse(f"<h2>❌ Cannot read client secret: {e}</h2>", status_code=500)

    resp = await _httpx.AsyncClient(timeout=15).post(
        "https://oauth2.googleapis.com/token",
        data={
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  _YT_CALLBACK_URL,   # clean URI, no query params
            "grant_type":    "authorization_code",
        },
    )
    if resp.status_code != 200:
        return HTMLResponse(
            f"<h2>❌ Token exchange failed</h2><pre>{resp.text}</pre>", status_code=500
        )

    token = resp.json()
    token["expires_at"] = _time.time() + token.get("expires_in", 3600)
    # Store absolute refresh_token expiry for the monitor script
    rte = token.get("refresh_token_expires_in")
    if rte:
        token["refresh_token_absolute_expiry"] = _time.time() + float(rte)

    # Preserve existing refresh_token if new response doesn't include one
    try:
        with open(token_path) as f:
            old = _json.load(f)
        if not token.get("refresh_token") and old.get("refresh_token"):
            token["refresh_token"] = old["refresh_token"]
    except Exception:
        pass

    with open(token_path, "w") as f:
        _json.dump(token, f, indent=2)

    channel = "MedMind EN" if account == "en" else "MedMind ES"
    return HTMLResponse(f"""
<html><body style="font-family:sans-serif;padding:40px;text-align:center">
<h1>✅ YouTube token renewed!</h1>
<p>Channel: <strong>{channel}</strong></p>
<p>Token saved. YouTube uploads will resume automatically.</p>
<p>You can close this tab.</p>
</body></html>
""")
