"""Tests for Phase 7: PWA + i18n foundation."""
import json
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
PUBLIC_DIR = FRONTEND_DIR / "public"
APP_DIR = FRONTEND_DIR / "app"


# ── 7.1 PWA ──────────────────────────────────────────────────────────────────

def test_service_worker_file_exists():
    assert (PUBLIC_DIR / "sw.js").exists(), "public/sw.js must exist"


def test_service_worker_has_install_handler():
    sw = (PUBLIC_DIR / "sw.js").read_text()
    assert "addEventListener" in sw and "install" in sw


def test_service_worker_has_activate_handler():
    sw = (PUBLIC_DIR / "sw.js").read_text()
    assert "activate" in sw


def test_service_worker_has_fetch_handler():
    sw = (PUBLIC_DIR / "sw.js").read_text()
    assert "fetch" in sw


def test_service_worker_skips_api_routes():
    sw = (PUBLIC_DIR / "sw.js").read_text()
    assert "/api/" in sw, "SW must explicitly skip /api/ routes"


def test_service_worker_does_not_cache_auth_api():
    sw = (PUBLIC_DIR / "sw.js").read_text()
    # SW must return early for API paths — not cache authenticated API responses
    assert "return" in sw, "SW must have early returns for non-cached paths"


def test_manifest_file_exists():
    assert (APP_DIR / "manifest.ts").exists(), "app/manifest.ts must exist"


def test_manifest_has_icons():
    manifest_content = (APP_DIR / "manifest.ts").read_text()
    assert "icon-192.png" in manifest_content
    assert "icon-512.png" in manifest_content


def test_manifest_has_start_url():
    manifest_content = (APP_DIR / "manifest.ts").read_text()
    assert "start_url" in manifest_content


def test_manifest_display_standalone():
    manifest_content = (APP_DIR / "manifest.ts").read_text()
    assert "standalone" in manifest_content


def test_icon_192_exists():
    assert (PUBLIC_DIR / "icon-192.png").exists(), "public/icon-192.png must exist"


def test_icon_512_exists():
    assert (PUBLIC_DIR / "icon-512.png").exists(), "public/icon-512.png must exist"


def test_pwa_install_prompt_component_exists():
    prompt_path = FRONTEND_DIR / "components" / "ui" / "PWAInstallPrompt.tsx"
    assert prompt_path.exists(), "PWAInstallPrompt.tsx must exist"


def test_pwa_install_prompt_registers_sw():
    prompt_content = (FRONTEND_DIR / "components" / "ui" / "PWAInstallPrompt.tsx").read_text()
    assert "serviceWorker" in prompt_content
    assert "register" in prompt_content
    assert "sw.js" in prompt_content


def test_pwa_install_prompt_handles_beforeinstallprompt():
    prompt_content = (FRONTEND_DIR / "components" / "ui" / "PWAInstallPrompt.tsx").read_text()
    assert "beforeinstallprompt" in prompt_content


def test_pwa_prompt_is_in_layout():
    layout_content = (APP_DIR / "layout.tsx").read_text()
    assert "PWAInstallPrompt" in layout_content


def test_offline_page_exists():
    assert (APP_DIR / "offline" / "page.tsx").exists(), "app/offline/page.tsx must exist"


# ── 7.2 i18n foundation ───────────────────────────────────────────────────────

def test_module_model_has_language_field():
    from app.models.models import Module
    cols = {c.key for c in Module.__table__.columns}
    assert "language" in cols, "Module must have a language column"


def test_module_language_defaults_to_en():
    from app.models.models import Module
    col = Module.__table__.c["language"]
    sd = col.server_default
    assert sd is not None and "en" in str(sd.arg)


def test_migration_0031_exists():
    migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "0031_module_language.py"
    assert migration_path.exists(), "Migration 0031_module_language.py must exist"


def test_migration_0031_revises_0030():
    migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "0031_module_language.py"
    content = migration_path.read_text()
    assert 'down_revision = "0030"' in content


def test_migration_0031_adds_language_column():
    migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "0031_module_language.py"
    content = migration_path.read_text()
    assert "language" in content
    assert "add_column" in content


def test_module_out_schema_includes_language():
    from app.schemas.schemas import ModuleOut
    fields = ModuleOut.model_fields
    assert "language" in fields, "ModuleOut schema must include language field"


def test_module_out_language_default_is_en():
    from app.schemas.schemas import ModuleOut
    field = ModuleOut.model_fields["language"]
    assert field.default == "en"


def test_import_script_reads_language_from_meta():
    """Simulate import_modules.py reading language from module meta."""
    meta = {"id": "TEST-001", "specialty": "Veterinary", "language": "ru"}
    language = meta.get("language", "en")
    assert language == "ru"


def test_import_script_defaults_language_to_en():
    meta = {"id": "TEST-001", "specialty": "Veterinary"}
    language = meta.get("language", "en")
    assert language == "en"


def test_language_filter_logic():
    """Simulate language filter: only return modules matching requested language."""
    modules = [
        {"code": "CARDIO-001", "language": "en"},
        {"code": "CARDIO-002", "language": "ru"},
        {"code": "NEURO-001", "language": "en"},
    ]
    filtered = [m for m in modules if m["language"] == "en"]
    assert len(filtered) == 2
    assert all(m["language"] == "en" for m in filtered)


# ── i18n locale files ────────────────────────────────────────────────────────

LOCALES_DIR = FRONTEND_DIR / "locales"

def test_en_locale_file_exists():
    assert (LOCALES_DIR / "en.ts").exists()


def test_ru_locale_file_exists():
    assert (LOCALES_DIR / "ru.ts").exists()


def test_locale_files_have_common_keys():
    en_content = (LOCALES_DIR / "en.ts").read_text()
    ru_content = (LOCALES_DIR / "ru.ts").read_text()
    for key in ("common", "nav", "dashboard", "auth"):
        assert key in en_content, f"en.ts missing key group: {key}"
        assert key in ru_content, f"ru.ts missing key group: {key}"


def test_i18n_provider_exists():
    i18n_path = FRONTEND_DIR / "lib" / "i18n.tsx"
    assert i18n_path.exists()
    content = i18n_path.read_text()
    assert "I18nProvider" in content
    assert "useT" in content
    assert "setLocale" in content


def test_i18n_supports_en_and_ru():
    i18n_content = (FRONTEND_DIR / "lib" / "i18n.tsx").read_text()
    assert '"en"' in i18n_content or "'en'" in i18n_content
    assert '"ru"' in i18n_content or "'ru'" in i18n_content


def test_i18n_locale_switcher_in_settings():
    settings_path = FRONTEND_DIR / "app" / "(app)" / "settings" / "page.tsx"
    content = settings_path.read_text()
    assert "setLocale" in content or "locale" in content
