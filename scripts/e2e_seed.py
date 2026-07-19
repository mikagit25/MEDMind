#!/usr/bin/env python3
"""
E2E seed script — idempotent. Creates test fixtures for Playwright smoke tests.

Usage:
    python scripts/e2e_seed.py [--api http://localhost:8000]
"""
import argparse
import sys
import requests

API = "http://localhost:8000/api/v1"

E2E_USER = {
    "email": "e2e_test@example.com",
    "password": "E2eTest1234!",
    "first_name": "E2E",
    "last_name": "Tester",
    "role": "student",
    "consent_terms": True,
    "consent_data_processing": True,
    "consent_marketing": False,
}

E2E_ADMIN = {
    "email": "e2e_admin@example.com",
    "password": "E2eAdmin1234!",
    "first_name": "E2E",
    "last_name": "Admin",
    "role": "student",
    "consent_terms": True,
    "consent_data_processing": True,
    "consent_marketing": False,
}

PROMO_CODE = "E2ETEST50"


def log(msg: str) -> None:
    print(f"[seed] {msg}", flush=True)


def register_or_login(api: str, user: dict) -> str:
    """Register user (idempotent) and return access token."""
    # Try login first
    r = requests.post(f"{api}/auth/login", json={
        "email": user["email"],
        "password": user["password"],
    }, timeout=10)
    if r.status_code == 200:
        log(f"Logged in as {user['email']}")
        return r.json()["access_token"]

    # Register
    r = requests.post(f"{api}/auth/register", json=user, timeout=10)
    if r.status_code in (200, 201):
        log(f"Registered {user['email']}")
        data = r.json()
        return data.get("access_token") or login(api, user)

    log(f"Failed to register/login {user['email']}: {r.status_code} {r.text[:200]}")
    sys.exit(1)


def login(api: str, user: dict) -> str:
    r = requests.post(f"{api}/auth/login", json={
        "email": user["email"],
        "password": user["password"],
    }, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def ensure_promo(api: str, admin_token: str) -> None:
    """Create E2ETEST50 promo code if it doesn't exist."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Check existing promos
    r = requests.get(f"{api}/admin/promo-codes", headers=headers, timeout=10)
    if r.status_code == 200:
        existing = [p.get("code") for p in r.json()]
        if PROMO_CODE in existing:
            log(f"Promo code {PROMO_CODE} already exists")
            return

    # Create promo
    r = requests.post(f"{api}/admin/promo-codes", json={
        "code": PROMO_CODE,
        "type": "trial",
        "tier": "student",
        "duration_days": 30,
        "max_uses": 1000,
        "description": "E2E test promo code",
    }, headers=headers, timeout=10)
    if r.status_code in (200, 201):
        log(f"Created promo code {PROMO_CODE}")
    elif r.status_code == 409:
        log(f"Promo code {PROMO_CODE} already exists (409)")
    else:
        log(f"Could not create promo (status {r.status_code}) — skipping")


def ensure_modules(api: str, admin_token: str) -> None:
    """Trigger module import to ensure at least one module exists."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{api}/content/modules?limit=1", headers=headers, timeout=10)
    if r.status_code == 200:
        modules = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        if modules:
            log(f"Modules already present ({len(modules)} visible)")
            return
    log("No modules found — ensure import_modules was run")


def complete_onboarding(api: str, token: str) -> None:
    """Complete onboarding for the test user (sets onboarding_completed=True)."""
    headers = {"Authorization": f"Bearer {token}"}
    # Check current state
    r = requests.get(f"{api}/auth/me", headers=headers, timeout=10)
    if r.status_code == 200 and r.json().get("onboarding_completed"):
        log("Onboarding already completed")
        return
    # Complete onboarding
    r = requests.post(f"{api}/auth/onboarding", json={
        "role": "student",
        "goal": "exam_prep",
        "daily_minutes": 30,
    }, headers=headers, timeout=10)
    if r.status_code == 200:
        log("Onboarding completed ✓")
    else:
        log(f"Onboarding call returned {r.status_code} — {r.text[:100]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=API)
    args = parser.parse_args()

    api = args.api.rstrip("/")
    log(f"Seeding against {api}")

    # Health check
    r = requests.get(f"{api.replace('/api/v1', '')}/health", timeout=10)
    if r.status_code != 200:
        log(f"Backend not healthy: {r.status_code}")
        sys.exit(1)
    log("Backend healthy")

    # Create test user and complete onboarding (so redirects don't block tests)
    token = register_or_login(api, E2E_USER)
    log(f"E2E user ready: {E2E_USER['email']}")
    complete_onboarding(api, token)

    # Try admin for promo/modules
    admin_token = register_or_login(api, E2E_ADMIN)
    complete_onboarding(api, admin_token)
    ensure_promo(api, admin_token)
    ensure_modules(api, admin_token)

    log("Seed complete ✓")
    print(f"E2E_USER_EMAIL={E2E_USER['email']}")
    print(f"E2E_USER_PASSWORD={E2E_USER['password']}")
    print(f"E2E_PROMO_CODE={PROMO_CODE}")


if __name__ == "__main__":
    main()
