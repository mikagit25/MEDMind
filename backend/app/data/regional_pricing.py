"""G3 — Regional / PPP pricing data.

Three tiers:
  A — US / EU / GCC (full price)
  B — Turkey / LatAm / Eastern Europe (~50 %)
  C — South Asia / Africa / Philippines / Egypt (~30 %)

Prices live here, not in DB, so a deploy is required to change them.
Stripe is charged in USD; local-currency display is informational only.
"""

from __future__ import annotations

# ── Base prices (USD, monthly unless noted) ──────────────────────────────────

BASE_PRICES_USD: dict[str, float] = {
    "student":    15.00,
    "pro":        40.00,
    "clinic":    199.00,
    "gulf_bundle": 29.00,
    "lifetime":  249.00,   # one-time
}

# ── Tier multipliers ──────────────────────────────────────────────────────────

TIER_MULTIPLIERS: dict[str, float] = {
    "A": 1.00,   # full price
    "B": 0.50,   # 50 %
    "C": 0.30,   # 30 %
}

# Minimum floor to avoid $1-ish charges (Stripe minimum is ~$0.50)
TIER_FLOORS_USD: dict[str, float] = {
    "A": 1.00,
    "B": 1.00,
    "C": 1.00,
}

# ── Country ISO-2 → pricing tier ─────────────────────────────────────────────

COUNTRY_TIER: dict[str, str] = {
    # ── Tier A: US / Anglosphere / EU / GCC ──────────────────────────────────
    "US": "A", "CA": "A", "GB": "A", "AU": "A", "NZ": "A",
    "IE": "A", "MT": "A",
    # EU-27
    "DE": "A", "FR": "A", "NL": "A", "BE": "A", "LU": "A",
    "AT": "A", "FI": "A", "SE": "A", "DK": "A", "NO": "A",
    "CH": "A", "IS": "A", "LI": "A",
    "IT": "A", "ES": "A", "PT": "A",
    "PL": "A", "CZ": "A", "SK": "A", "HU": "A", "SI": "A",
    "HR": "A", "EE": "A", "LV": "A", "LT": "A",
    "CY": "A", "GR": "A",
    # GCC
    "SA": "A", "AE": "A", "QA": "A", "KW": "A", "BH": "A", "OM": "A",
    # Other high-income
    "SG": "A", "JP": "A", "KR": "A", "IL": "A", "HK": "A",

    # ── Tier B: Turkey / LatAm / Eastern Europe / CIS ────────────────────────
    "TR": "B",
    # LatAm
    "MX": "B", "BR": "B", "CO": "B", "AR": "B", "CL": "B", "PE": "B",
    "EC": "B", "VE": "B", "BO": "B", "PY": "B", "UY": "B",
    "CR": "B", "PA": "B", "DO": "B", "GT": "B", "HN": "B",
    # CIS / Eastern Europe
    "RU": "B", "UA": "B", "BY": "B", "MD": "B",
    "GE": "B", "AM": "B", "AZ": "B",
    "KZ": "B", "UZ": "B", "KG": "B", "TJ": "B", "TM": "B",
    "RO": "B", "BG": "B", "RS": "B", "BA": "B", "MK": "B",
    "AL": "B", "ME": "B", "XK": "B",
    # Middle East (non-GCC, mid-income)
    "IR": "B", "LY": "B",
    # South-East Asia (mid-income)
    "MY": "B", "TH": "B", "CN": "B",

    # ── Tier C: South Asia / Africa / Philippines / Egypt ────────────────────
    # South Asia
    "IN": "C", "PK": "C", "BD": "C", "LK": "C", "NP": "C", "MV": "C",
    # South-East Asia (lower-income)
    "PH": "C", "ID": "C", "VN": "C", "MM": "C", "KH": "C", "LA": "C",
    # MENA lower-income
    "EG": "C", "JO": "C", "LB": "C", "IQ": "C", "YE": "C", "SY": "C",
    "MA": "C", "TN": "C", "DZ": "C", "LY": "C", "SD": "C",
    # Sub-Saharan Africa
    "NG": "C", "KE": "C", "GH": "C", "ET": "C", "TZ": "C", "UG": "C",
    "ZA": "C", "ZM": "C", "ZW": "C", "MZ": "C", "RW": "C", "SN": "C",
    "CM": "C", "CI": "C", "ML": "C", "BF": "C", "NE": "C", "TD": "C",
    "SO": "C", "DJ": "C", "MG": "C", "MW": "C", "BI": "C",
    # Central Asia (lower)
    "AF": "C",
}

DEFAULT_TIER = "A"  # unknown country → full price (no under-pricing risk)


# ── Helper functions ──────────────────────────────────────────────────────────

def get_tier(country_code: str | None) -> str:
    """Return pricing tier for a 2-letter ISO country code. Default: A."""
    if not country_code:
        return DEFAULT_TIER
    return COUNTRY_TIER.get(country_code.upper(), DEFAULT_TIER)


def get_price(plan: str, tier: str) -> float:
    """Return regional price in USD, rounded to 2 dp, no lower than floor."""
    base = BASE_PRICES_USD.get(plan, 0.0)
    mult = TIER_MULTIPLIERS.get(tier, 1.0)
    floor = TIER_FLOORS_USD.get(tier, 1.0)
    return max(round(base * mult, 2), floor)


def price_table(tier: str) -> dict[str, float]:
    """Return full price table for a given tier."""
    return {plan: get_price(plan, tier) for plan in BASE_PRICES_USD}


def all_tiers_table() -> dict[str, dict[str, float]]:
    """Return prices for all tiers — used in admin UI."""
    return {t: price_table(t) for t in TIER_MULTIPLIERS}
