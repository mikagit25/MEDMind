"""G3 — Regional pricing tests.

Covers:
- Country → tier mapping correctness
- Price calculations and floors
- Anti-abuse: no under-pricing for unknown countries
- region_service helpers
- payments route imports pricing helpers
- User model has billing fields
- Config has PayPal feature flag
"""

import pytest


# ── G3.1 Regional pricing data layer ─────────────────────────────────────────

class TestCountryTierMapping:
    def test_us_is_tier_a(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("US") == "A"

    def test_gcc_countries_are_tier_a(self):
        from app.data.regional_pricing import get_tier
        for cc in ["SA", "AE", "QA", "KW", "BH", "OM"]:
            assert get_tier(cc) == "A", f"{cc} should be Tier A (GCC)"

    def test_eu_countries_are_tier_a(self):
        from app.data.regional_pricing import get_tier
        for cc in ["DE", "FR", "NL", "GB", "IT", "ES"]:
            assert get_tier(cc) == "A", f"{cc} should be Tier A (EU)"

    def test_turkey_is_tier_b(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("TR") == "B"

    def test_latam_countries_are_tier_b(self):
        from app.data.regional_pricing import get_tier
        for cc in ["MX", "BR", "CO", "AR", "CL"]:
            assert get_tier(cc) == "B", f"{cc} should be Tier B (LatAm)"

    def test_russia_is_tier_b(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("RU") == "B"

    def test_philippines_is_tier_c(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("PH") == "C"

    def test_egypt_is_tier_c(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("EG") == "C"

    def test_india_is_tier_c(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("IN") == "C"

    def test_pakistan_is_tier_c(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("PK") == "C"

    def test_nigeria_is_tier_c(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("NG") == "C"

    def test_unknown_country_defaults_to_a(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("ZZ") == "A", "Unknown country must default to full price"

    def test_none_country_defaults_to_a(self):
        from app.data.regional_pricing import get_tier
        assert get_tier(None) == "A", "None country must default to full price"

    def test_lowercase_country_handled(self):
        from app.data.regional_pricing import get_tier
        assert get_tier("ph") == "C", "Should handle lowercase ISO codes"


class TestPriceCalculations:
    def test_tier_a_price_equals_base(self):
        from app.data.regional_pricing import get_price, BASE_PRICES_USD
        for plan, base in BASE_PRICES_USD.items():
            assert get_price(plan, "A") == base, f"Tier A {plan} should equal base"

    def test_tier_b_price_is_50pct(self):
        from app.data.regional_pricing import get_price, BASE_PRICES_USD
        for plan, base in BASE_PRICES_USD.items():
            b_price = get_price(plan, "B")
            assert b_price == round(base * 0.5, 2), f"Tier B {plan}: {b_price} != {round(base*0.5,2)}"

    def test_tier_c_price_is_30pct(self):
        from app.data.regional_pricing import get_price, BASE_PRICES_USD
        for plan, base in BASE_PRICES_USD.items():
            c_price = get_price(plan, "C")
            assert c_price == round(base * 0.3, 2), f"Tier C {plan}: {c_price} != {round(base*0.3,2)}"

    def test_prices_never_below_floor(self):
        from app.data.regional_pricing import get_price, TIER_FLOORS_USD
        for tier, floor in TIER_FLOORS_USD.items():
            for plan in ["student", "pro", "clinic", "gulf_bundle", "lifetime"]:
                price = get_price(plan, tier)
                assert price >= floor, f"{plan}/{tier}: price {price} < floor {floor}"

    def test_student_tier_c_is_correct(self):
        from app.data.regional_pricing import get_price
        price = get_price("student", "C")
        assert price == round(15.0 * 0.3, 2)  # 4.5

    def test_pro_tier_b_is_correct(self):
        from app.data.regional_pricing import get_price
        price = get_price("pro", "B")
        assert price == round(40.0 * 0.5, 2)  # 20.0

    def test_price_table_returns_all_plans(self):
        from app.data.regional_pricing import price_table, BASE_PRICES_USD
        table = price_table("C")
        assert set(table.keys()) == set(BASE_PRICES_USD.keys())

    def test_all_tiers_table_has_three_tiers(self):
        from app.data.regional_pricing import all_tiers_table
        tbl = all_tiers_table()
        assert set(tbl.keys()) == {"A", "B", "C"}

    def test_unknown_tier_defaults_to_full_price(self):
        from app.data.regional_pricing import get_price, BASE_PRICES_USD
        price = get_price("student", "X")  # unknown tier
        assert price == BASE_PRICES_USD["student"]


# ── G3.2 Region service ───────────────────────────────────────────────────────

class TestRegionServiceImport:
    def test_region_service_imports(self):
        from app.services import region_service
        assert hasattr(region_service, "resolve_pricing_tier")

    def test_can_change_billing_country_new_user(self):
        from app.services.region_service import can_change_billing_country

        class FakeUser:
            billing_country = None

        assert can_change_billing_country(FakeUser()) is True

    def test_cannot_change_billing_country_after_set(self):
        from app.services.region_service import can_change_billing_country

        class FakeUser:
            billing_country = "PH"

        assert can_change_billing_country(FakeUser()) is False

    def test_ip_cache_bounded(self):
        from app.services.region_service import _ip_cache, _IP_CACHE_MAX
        assert _IP_CACHE_MAX > 0


# ── G3.3 User model fields ────────────────────────────────────────────────────

class TestUserModelBillingFields:
    def test_user_has_billing_country(self):
        from app.models.models import User
        assert hasattr(User, "billing_country")

    def test_user_has_billing_region(self):
        from app.models.models import User
        assert hasattr(User, "billing_region")

    def test_user_has_billing_region_changed_at(self):
        from app.models.models import User
        assert hasattr(User, "billing_region_changed_at")


# ── G3.4 Config PayPal feature flag ──────────────────────────────────────────

class TestConfigPayPalFlag:
    def test_paypal_enabled_flag_exists(self):
        from app.core.config import settings
        assert hasattr(settings, "PAYPAL_ENABLED")

    def test_paypal_enabled_defaults_false(self):
        from app.core.config import settings
        assert settings.PAYPAL_ENABLED is False

    def test_paypal_client_id_exists(self):
        from app.core.config import settings
        assert hasattr(settings, "PAYPAL_CLIENT_ID")

    def test_paypal_mode_exists(self):
        from app.core.config import settings
        assert hasattr(settings, "PAYPAL_MODE")


# ── G3.5 Pricing API route ────────────────────────────────────────────────────

class TestPricingRouteStructure:
    def test_pricing_router_importable(self):
        from app.api.v1.routes.pricing import router
        assert router.prefix == "/pricing"

    def test_regional_endpoint_registered(self):
        from app.api.v1.routes.pricing import router
        paths = [r.path for r in router.routes]
        assert any("regional" in p for p in paths)

    def test_all_tiers_endpoint_registered(self):
        from app.api.v1.routes.pricing import router
        paths = [r.path for r in router.routes]
        assert any("all-tiers" in p for p in paths)


# ── G3.6 Payments route uses regional pricing ─────────────────────────────────

class TestPaymentsRouteG3Integration:
    def test_payments_imports_regional_pricing(self):
        import pathlib
        src = pathlib.Path("app/api/v1/routes/payments.py").read_text()
        assert "from app.data.regional_pricing import" in src

    def test_payments_imports_region_service(self):
        import pathlib
        src = pathlib.Path("app/api/v1/routes/payments.py").read_text()
        assert "from app.services.region_service import" in src

    def test_payments_captures_billing_country_in_metadata(self):
        import pathlib
        src = pathlib.Path("app/api/v1/routes/payments.py").read_text()
        assert "billing_country" in src

    def test_payments_captures_billing_region_in_metadata(self):
        import pathlib
        src = pathlib.Path("app/api/v1/routes/payments.py").read_text()
        assert "billing_region" in src

    def test_activate_subscription_sets_billing_country(self):
        import pathlib
        src = pathlib.Path("app/api/v1/routes/payments.py").read_text()
        assert "user.billing_country" in src
        assert "user.billing_region" in src


# ── G3.7 Tiers are comprehensive (no coverage gaps for key markets) ───────────

class TestMarketCoverage:
    """Key target markets for Gulf+ES expansion must be in the tier map."""

    def test_target_markets_all_mapped(self):
        from app.data.regional_pricing import COUNTRY_TIER
        required = {
            "PH": "C",  # Philippines — major Gulf nurse source
            "IN": "C",  # India — top nursing workforce
            "EG": "C",  # Egypt — MENA hub
            "PK": "C",  # Pakistan
            "TR": "B",  # Turkey — KPSS market
            "MX": "B",  # Mexico — Spanish LatAm
            "CO": "B",  # Colombia
            "BR": "B",  # Brazil
            "SA": "A",  # Saudi — GCC full price
            "AE": "A",  # UAE
        }
        for cc, expected_tier in required.items():
            assert COUNTRY_TIER.get(cc) == expected_tier, (
                f"Market {cc} must be Tier {expected_tier}"
            )
