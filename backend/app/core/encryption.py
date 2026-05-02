"""
Email field encryption using Fernet (AES-128-CBC with HMAC-SHA256).

Usage:
    from app.core.encryption import encrypt_email, decrypt_email

    stored = encrypt_email("user@example.com")   # store this in DB
    original = decrypt_email(stored)              # retrieve original

If ENCRYPTION_KEY is not set (dev mode), returns the value unchanged so
existing plain-text emails continue to work without migration.
"""
import base64
import logging

log = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet

    from app.core.config import settings
    key = settings.ENCRYPTION_KEY.strip()
    if not key:
        return None  # dev mode — no encryption

    try:
        from cryptography.fernet import Fernet
        # Accept either a raw 32-byte hex string or a proper Fernet URL-safe base64 key
        if len(key) == 44 and key.endswith("="):
            # Already a valid Fernet key
            fernet_key = key.encode()
        elif len(key) == 64:
            # Hex-encoded 32 bytes → convert to Fernet format
            raw = bytes.fromhex(key)
            fernet_key = base64.urlsafe_b64encode(raw)
        else:
            fernet_key = key.encode()

        _fernet = Fernet(fernet_key)
        return _fernet
    except Exception as exc:
        log.error("Failed to initialise Fernet encryption: %s", exc)
        return None


def encrypt_email(email: str) -> str:
    """Encrypt email for DB storage. Returns ciphertext or plain email in dev."""
    f = _get_fernet()
    if f is None:
        return email
    try:
        return f.encrypt(email.lower().encode()).decode()
    except Exception as exc:
        log.error("Email encryption failed: %s", exc)
        return email


def decrypt_email(stored: str) -> str:
    """Decrypt email from DB. Returns plain email (handles both encrypted and plain)."""
    if not stored:
        return stored
    f = _get_fernet()
    if f is None:
        return stored
    try:
        return f.decrypt(stored.encode()).decode()
    except Exception:
        # Not encrypted (e.g., existing plain-text record) — return as-is
        return stored


def email_search_hash(email: str) -> str:
    """
    Returns a SHA-256 HMAC of the email for equality-search without decryption.
    This is stored in email_hash column and used in login queries.
    """
    import hashlib
    import hmac
    from app.core.config import settings
    key = (settings.ENCRYPTION_KEY or settings.JWT_SECRET_KEY).encode()
    return hmac.new(key, email.lower().encode(), hashlib.sha256).hexdigest()
