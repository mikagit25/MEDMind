"""Authentication routes."""
from datetime import datetime, timedelta
import hashlib
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, hash_email,
    create_access_token, create_refresh_token,
)
from app.core.config import settings
from app.models.models import User, RefreshToken, UserConsent
from pydantic import BaseModel
from app.schemas.schemas import UserRegister, UserLogin, TokenResponse, RefreshRequest, UserOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# Simple in-memory rate limiting for auth endpoints (login/register)
# Tracks failed attempts: {ip: [timestamp, ...]}
_failed_attempts: dict = {}
AUTH_RATE_LIMIT = 10  # max attempts per window
AUTH_RATE_WINDOW = 300  # 5 minutes in seconds


def check_auth_rate_limit(request: Request) -> None:
    """Block IPs with too many failed auth attempts."""
    ip = request.client.host if request.client else "unknown"
    now = datetime.utcnow().timestamp()
    attempts = _failed_attempts.get(ip, [])
    # Keep only attempts within the window
    attempts = [t for t in attempts if now - t < AUTH_RATE_WINDOW]
    if len(attempts) >= AUTH_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait 5 minutes.",
        )
    _failed_attempts[ip] = attempts


def record_failed_attempt(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = datetime.utcnow().timestamp()
    attempts = _failed_attempts.get(ip, [])
    attempts.append(now)
    _failed_attempts[ip] = attempts


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferences: Optional[dict] = None


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    check_auth_rate_limit(request)
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == data.email.lower()))
    if existing.scalar_one_or_none():
        record_failed_attempt(request)
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email.lower(),
        email_hash=hash_email(data.email),
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        subscription_tier="free",
    )
    db.add(user)
    await db.flush()  # get user.id

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

    await db.commit()
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

    # Send welcome email (non-blocking)
    from app.services.email_service import send_welcome_email
    try:
        send_welcome_email(user.email, user.first_name or "there")
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
    check_auth_rate_limit(request)
    result = await db.execute(select(User).where(User.email == data.email.lower(), User.is_active == True))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        record_failed_attempt(request)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(str(user.id))
    raw_refresh, hashed_refresh = create_refresh_token()

    refresh = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
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
    if data.preferences is not None:
        user.preferences = {**(user.preferences or {}), **data.preferences}
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/onboarding", response_model=UserOut)
async def complete_onboarding(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Save onboarding preferences and mark onboarding complete."""
    user.preferences = {**(user.preferences or {}), **data}
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
    check_auth_rate_limit(request)

    result = await db.execute(
        select(User).where(User.email == data.email.lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user:
        # Generate a secure token (valid 1 hour)
        import secrets
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires = datetime.utcnow() + timedelta(hours=1)

        # Store in user preferences (simple approach — no extra table needed)
        user.preferences = {
            **(user.preferences or {}),
            "_reset_token_hash": token_hash,
            "_reset_token_expires": expires.isoformat(),
        }
        await db.commit()

        # Send reset email (SMTP if configured, else logs to console)
        from app.services.email_service import send_password_reset
        send_password_reset(data.email.lower(), raw_token)

    return {"detail": "If this email is registered, a reset link has been sent."}


@router.post("/reset-password", status_code=200)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate reset token and update password."""
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()

    # Find user with matching reset token
    from sqlalchemy import cast
    from sqlalchemy.dialects.postgresql import JSONB
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.preferences["_reset_token_hash"].as_string() == token_hash,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    prefs = user.preferences or {}
    expires_str = prefs.get("_reset_token_expires")
    if not expires_str or datetime.fromisoformat(expires_str) < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")

    # Validate new password
    if len(data.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    user.password_hash = hash_password(data.new_password)
    # Clear reset token
    prefs.pop("_reset_token_hash", None)
    prefs.pop("_reset_token_expires", None)
    user.preferences = prefs

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
    async with httpx.AsyncClient() as client:
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

    # Upsert user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # New user via Google — create account
        user = User(
            email=email,
            email_hash=hash_email(email),
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            oauth_provider="google",
            oauth_id=google_id,
            is_verified=True,
            subscription_tier="free",
        )
        db.add(user)
        await db.flush()
        # GDPR consent (implicit via OAuth)
        db.add(UserConsent(user_id=user.id, consent_type="terms", version="1.0"))
        db.add(UserConsent(user_id=user.id, consent_type="privacy", version="1.0"))
        await db.commit()
        await db.refresh(user)
    else:
        # Existing user — update OAuth info if needed
        if not user.oauth_provider:
            user.oauth_provider = "google"
            user.oauth_id = google_id
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        user.is_verified = True
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

    # Redirect to frontend with tokens in query params
    # Frontend reads them from URL and stores in localStorage
    from fastapi.responses import RedirectResponse
    import urllib.parse
    needs_onboarding = not user.onboarding_completed
    redirect_url = (
        f"{settings.FRONTEND_URL}/auth/google/success"
        f"?access_token={urllib.parse.quote(access_token)}"
        f"&refresh_token={urllib.parse.quote(raw_refresh)}"
        f"&onboarding={'1' if needs_onboarding else '0'}"
    )
    return RedirectResponse(url=redirect_url)
