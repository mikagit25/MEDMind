"""E2: Email encryption / decryption tests."""
import base64
import os
import importlib
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fernet_key() -> str:
    """Generate a valid Fernet key (URL-safe base64, 32 raw bytes)."""
    raw = os.urandom(32)
    return base64.urlsafe_b64encode(raw).decode()


def _reload_encryption(key: str):
    """Reload encryption module with a specific ENCRYPTION_KEY."""
    import app.core.encryption as enc_mod

    # Reset cached _fernet instance so _get_fernet() picks up the new key
    enc_mod._fernet = None

    import app.core.config as config_mod
    config_mod.settings.ENCRYPTION_KEY = key

    importlib.reload(enc_mod)
    return enc_mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEncryptDecrypt:
    def test_round_trip(self):
        """Encrypted value decrypts back to original email."""
        enc = _reload_encryption(_make_fernet_key())
        email = "doctor@hospital.example.com"
        cipher = enc.encrypt_email(email)
        assert cipher != email, "ciphertext should not equal plaintext"
        assert enc.decrypt_email(cipher) == email

    def test_email_normalised_to_lowercase(self):
        """Encryption normalises to lowercase so case doesn't matter on login."""
        enc = _reload_encryption(_make_fernet_key())
        cipher = enc.encrypt_email("User@Example.COM")
        assert enc.decrypt_email(cipher) == "user@example.com"

    def test_no_key_passthrough(self):
        """When ENCRYPTION_KEY is empty, emails are stored plain (dev mode)."""
        enc = _reload_encryption("")
        email = "plain@test.com"
        assert enc.encrypt_email(email) == email
        assert enc.decrypt_email(email) == email

    def test_decrypt_plain_text_is_safe(self):
        """decrypt_email on a non-encrypted string returns it unchanged."""
        enc = _reload_encryption(_make_fernet_key())
        assert enc.decrypt_email("just_plain_email@example.com") == "just_plain_email@example.com"

    def test_hex_key_accepted(self):
        """A 64-char hex string (raw 32 bytes hex-encoded) is also accepted."""
        hex_key = os.urandom(32).hex()  # 64 chars
        enc = _reload_encryption(hex_key)
        email = "test@medmind.app"
        cipher = enc.encrypt_email(email)
        assert enc.decrypt_email(cipher) == email

    def test_different_keys_produce_different_ciphertexts(self):
        """Two different keys produce different ciphertexts for same email."""
        enc1 = _reload_encryption(_make_fernet_key())
        enc2 = _reload_encryption(_make_fernet_key())
        email = "same@email.com"
        c1 = enc1.encrypt_email(email)
        c2 = enc2.encrypt_email(email)
        assert c1 != c2

    def test_ciphertext_changes_on_each_call(self):
        """Fernet uses a random IV so same plaintext → different ciphertext each time."""
        enc = _reload_encryption(_make_fernet_key())
        email = "test@example.com"
        c1 = enc.encrypt_email(email)
        c2 = enc.encrypt_email(email)
        assert c1 != c2  # different IVs


class TestEmailSearchHash:
    def test_hash_is_deterministic(self):
        """Same email + same key always produces same hash."""
        import app.core.config as config_mod
        config_mod.settings.ENCRYPTION_KEY = _make_fernet_key()

        from app.core.encryption import email_search_hash
        h1 = email_search_hash("find@example.com")
        h2 = email_search_hash("find@example.com")
        assert h1 == h2

    def test_hash_differs_for_different_emails(self):
        """Different emails produce different hashes."""
        from app.core.encryption import email_search_hash
        assert email_search_hash("a@example.com") != email_search_hash("b@example.com")

    def test_hash_is_case_insensitive(self):
        """Hash ignores case so login works regardless of email capitalisation."""
        from app.core.encryption import email_search_hash
        assert email_search_hash("User@Example.COM") == email_search_hash("user@example.com")
