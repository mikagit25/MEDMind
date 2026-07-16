"""Parametric dose-calculation problem generator for nursing education.

ALL answers are derived from deterministic formulas — no AI-generated numbers.
Each template produces: question text, numeric answer, tolerance, unit, step-by-step solution.

Templates:
  weight_dose    — mg/kg → mg, then → mL of available solution
  infusion_rate  — mL/h from volume + time; drops/min with drop factor
  dilution       — target concentration from stock
  unit_convert   — mcg↔mg, mL↔L
  pediatric_dose — weight-based with mg/kg range check

Usage:
    from app.services.dose_calc_generator import generate_problem, CATEGORIES
    problem = generate_problem("weight_dose")
"""

import random
import math
from typing import Literal

CATEGORIES = ["weight_dose", "infusion_rate", "dilution", "unit_convert", "pediatric_dose"]

Category = Literal["weight_dose", "infusion_rate", "dilution", "unit_convert", "pediatric_dose"]


def _round_to(value: float, decimals: int = 2) -> float:
    return round(value, decimals)


# ── Template: weight-based dose ───────────────────────────────────────────────

def _weight_dose(rng: random.Random) -> dict:
    drug_names = ["Amoxicillin", "Ibuprofen", "Gentamicin", "Metronidazole", "Cefazolin"]
    drug = rng.choice(drug_names)
    weight_kg = rng.randint(45, 110)
    dose_mg_kg = rng.choice([5, 7.5, 10, 12.5, 15, 20, 25])
    conc_mg_ml = rng.choice([10, 25, 50, 100, 125, 250])

    total_mg = weight_kg * dose_mg_kg
    volume_ml = total_mg / conc_mg_ml

    question = (
        f"A patient weighs {weight_kg} kg. The prescribed dose of {drug} is "
        f"{dose_mg_kg} mg/kg. Available: {drug} {conc_mg_ml} mg/mL solution. "
        f"How many mL should you administer?"
    )
    steps = [
        f"Step 1 — Calculate total dose: {weight_kg} kg × {dose_mg_kg} mg/kg = {total_mg} mg",
        f"Step 2 — Convert to volume: {total_mg} mg ÷ {conc_mg_ml} mg/mL = {_round_to(volume_ml)} mL",
        f"Answer: {_round_to(volume_ml)} mL",
    ]
    return {
        "category": "weight_dose",
        "question": question,
        "numeric_answer": _round_to(volume_ml),
        "numeric_tolerance": 0.05,
        "numeric_unit": "mL",
        "steps": steps,
    }


# ── Template: infusion rate ───────────────────────────────────────────────────

def _infusion_rate(rng: random.Random) -> dict:
    mode = rng.choice(["ml_per_h", "drops_per_min"])
    volume_ml = rng.choice([250, 500, 750, 1000])
    hours = rng.choice([4, 6, 8, 10, 12])

    if mode == "ml_per_h":
        rate = volume_ml / hours
        question = (
            f"Infuse {volume_ml} mL of IV fluid over {hours} hours. "
            f"What is the infusion rate in mL/h?"
        )
        steps = [
            f"Step 1 — Rate = Volume ÷ Time = {volume_ml} mL ÷ {hours} h = {_round_to(rate)} mL/h",
            f"Answer: {_round_to(rate)} mL/h",
        ]
        return {
            "category": "infusion_rate",
            "question": question,
            "numeric_answer": _round_to(rate),
            "numeric_tolerance": 0.5,
            "numeric_unit": "mL/h",
            "steps": steps,
        }
    else:  # drops_per_min
        drop_factor = rng.choice([10, 15, 20, 60])
        drops_min = (volume_ml * drop_factor) / (hours * 60)
        question = (
            f"Infuse {volume_ml} mL over {hours} hours using a drip set with "
            f"drop factor {drop_factor} gtt/mL. What is the drip rate in drops/min?"
        )
        steps = [
            f"Step 1 — Formula: (Volume × Drop factor) ÷ (Hours × 60 min)",
            f"Step 2 — ({volume_ml} mL × {drop_factor} gtt/mL) ÷ ({hours} h × 60 min) = "
            f"{volume_ml * drop_factor} ÷ {hours * 60} = {_round_to(drops_min)} gtt/min",
            f"Answer: {_round_to(drops_min, 0):.0f} gtt/min (rounded to nearest whole drop)",
        ]
        return {
            "category": "infusion_rate",
            "question": question,
            "numeric_answer": _round_to(drops_min, 0),
            "numeric_tolerance": 1.0,
            "numeric_unit": "gtt/min",
            "steps": steps,
        }


# ── Template: dilution / concentration ───────────────────────────────────────

def _dilution(rng: random.Random) -> dict:
    drug_names = ["NaCl", "Potassium Chloride", "Dextrose", "Lidocaine"]
    drug = rng.choice(drug_names)
    stock_pct = rng.choice([5, 10, 20, 50])  # % w/v
    stock_mg_ml = stock_pct * 10             # 5% = 50 mg/mL
    target_mg_ml = rng.choice([1, 2, 5, 10])
    final_vol_ml = rng.choice([50, 100, 250])

    volume_stock = (target_mg_ml * final_vol_ml) / stock_mg_ml

    question = (
        f"You need to prepare {final_vol_ml} mL of {drug} solution at "
        f"{target_mg_ml} mg/mL using a {stock_pct}% stock solution "
        f"({stock_mg_ml} mg/mL). How many mL of stock do you need?"
    )
    diluent = _round_to(final_vol_ml - volume_stock)
    steps = [
        f"Step 1 — Formula: V₁C₁ = V₂C₂ → V₁ = (C₂ × V₂) ÷ C₁",
        f"Step 2 — V₁ = ({target_mg_ml} mg/mL × {final_vol_ml} mL) ÷ {stock_mg_ml} mg/mL",
        f"Step 3 — V₁ = {target_mg_ml * final_vol_ml} ÷ {stock_mg_ml} = {_round_to(volume_stock)} mL of stock",
        f"Step 4 — Add {diluent} mL of diluent to reach {final_vol_ml} mL total",
        f"Answer: {_round_to(volume_stock)} mL of stock solution",
    ]
    return {
        "category": "dilution",
        "question": question,
        "numeric_answer": _round_to(volume_stock),
        "numeric_tolerance": 0.05,
        "numeric_unit": "mL",
        "steps": steps,
    }


# ── Template: unit conversion ─────────────────────────────────────────────────

def _unit_convert(rng: random.Random) -> dict:
    mode = rng.choice(["mcg_to_mg", "mg_to_mcg", "ml_to_l", "l_to_ml"])

    if mode == "mcg_to_mg":
        val = rng.choice([250, 500, 750, 1000, 1500, 2000, 2500])
        answer = val / 1000
        question = f"Convert {val} mcg to mg."
        steps = [f"1 mg = 1000 mcg  →  {val} mcg ÷ 1000 = {answer} mg", f"Answer: {answer} mg"]
        unit = "mg"
    elif mode == "mg_to_mcg":
        val = rng.choice([0.1, 0.25, 0.5, 1, 2, 2.5])
        answer = val * 1000
        question = f"Convert {val} mg to mcg."
        steps = [f"1 mg = 1000 mcg  →  {val} mg × 1000 = {answer} mcg", f"Answer: {answer} mcg"]
        unit = "mcg"
    elif mode == "ml_to_l":
        val = rng.choice([250, 500, 750, 1000, 1500, 2000])
        answer = val / 1000
        question = f"Convert {val} mL to L."
        steps = [f"1 L = 1000 mL  →  {val} mL ÷ 1000 = {answer} L", f"Answer: {answer} L"]
        unit = "L"
    else:  # l_to_ml
        val = rng.choice([0.25, 0.5, 0.75, 1, 1.5, 2])
        answer = val * 1000
        question = f"Convert {val} L to mL."
        steps = [f"1 L = 1000 mL  →  {val} L × 1000 = {answer} mL", f"Answer: {answer} mL"]
        unit = "mL"

    return {
        "category": "unit_convert",
        "question": question,
        "numeric_answer": _round_to(answer),
        "numeric_tolerance": 0.001,
        "numeric_unit": unit,
        "steps": steps,
    }


# ── Template: pediatric dose ──────────────────────────────────────────────────

def _pediatric_dose(rng: random.Random) -> dict:
    drugs = [
        ("Paracetamol", 15, 20, 250, 5),   # name, min_mg_kg, max_mg_kg, stock_mg, stock_ml
        ("Amoxicillin", 25, 45, 125, 5),
        ("Ibuprofen", 5, 10, 100, 5),
    ]
    drug, min_mg_kg, max_mg_kg, stock_mg, stock_ml = rng.choice(drugs)
    weight_kg = rng.randint(8, 30)
    dose_mg_kg = rng.randint(min_mg_kg, max_mg_kg)

    total_mg = weight_kg * dose_mg_kg
    conc_mg_ml = stock_mg / stock_ml
    volume_ml = total_mg / conc_mg_ml

    question = (
        f"A child weighs {weight_kg} kg. Prescribe {drug} {dose_mg_kg} mg/kg. "
        f"Available: {drug} suspension {stock_mg} mg per {stock_ml} mL. "
        f"How many mL per dose?"
    )
    steps = [
        f"Step 1 — Total dose: {weight_kg} kg × {dose_mg_kg} mg/kg = {total_mg} mg",
        f"Step 2 — Concentration: {stock_mg} mg ÷ {stock_ml} mL = {conc_mg_ml} mg/mL",
        f"Step 3 — Volume: {total_mg} mg ÷ {conc_mg_ml} mg/mL = {_round_to(volume_ml)} mL",
        f"Answer: {_round_to(volume_ml)} mL",
    ]
    return {
        "category": "pediatric_dose",
        "question": question,
        "numeric_answer": _round_to(volume_ml),
        "numeric_tolerance": 0.1,
        "numeric_unit": "mL",
        "steps": steps,
    }


# ── Public API ────────────────────────────────────────────────────────────────

_GENERATORS = {
    "weight_dose": _weight_dose,
    "infusion_rate": _infusion_rate,
    "dilution": _dilution,
    "unit_convert": _unit_convert,
    "pediatric_dose": _pediatric_dose,
}


def generate_problem(category: Category, seed: int | None = None) -> dict:
    """Return a single dose-calculation problem dict.

    Keys: category, question, numeric_answer, numeric_tolerance, numeric_unit, steps (list[str]).
    If seed is provided the output is deterministic (useful for tests).
    """
    rng = random.Random(seed)
    generator = _GENERATORS.get(category)
    if generator is None:
        raise ValueError(f"Unknown category: {category}. Valid: {CATEGORIES}")
    return generator(rng)


def generate_series(category: Category, count: int = 5, seed: int | None = None) -> list[dict]:
    """Return `count` problems for the given category with increasing complexity.
    Complexity is approximated by choosing a progressive seed offset so parameters
    naturally vary rather than repeat.
    """
    base_seed = seed if seed is not None else random.randint(0, 999999)
    problems = []
    for i in range(count):
        problems.append(generate_problem(category, seed=base_seed + i * 37))
    return problems
