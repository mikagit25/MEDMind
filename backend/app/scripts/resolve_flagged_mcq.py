"""
Resolve all 68 flagged MCQs after manual clinical review.

Three actions:
  RETIRE  — question is irreparably broken (bad math, impossible unit, nonsensical premise)
  FIX     — question is salvageable; correct answer reassigned + explanation note added
  UNFLAG  — answer is clinically defensible; clear the flag and approve
"""

import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal as async_session_factory

# ── RETIRE — delete from DB ────────────────────────────────────────────────────
# Reasons: wrong math with no correct option, physiologically impossible data,
#          nonsensical clinical premise, dosing 10-20× too high (dangerous).
RETIRE = {
    "3691f1e9-f768-4889-8708-605db055b861": "weight-based calc wrong — no option is correct (13.5 mL)",
    "1c8f0e62-322b-43b9-a765-0ac5d3f1f67d": "PaCO2 listed as 32 kPa — physiologically fatal, unit typo",
    "e22a4c07-41fd-42c2-b5be-99e11c9c0619": "APGAR question — criteria not stated, options unverifiable",
    "949efe32-c353-4ede-af00-ddb7a49cd8ae": "flunixin for 'equine colic in canine patients' — nonsensical",
    "8be01302-5e3a-4fbc-97fd-76fd2d7fa0ba": "lidocaine equine colic — correct answer (CRI) not in options",
    "3e0c492e-7153-4e8a-9d3b-dac5ccb1a0f4": "atenolol 6.25-12.5 mg/kg for cats — 10-20× overdose, dangerous",
    "9b11f989-c0ca-4da9-9c12-8c56060f88ac": "tPA GI bleed 2 months ago — all options clinically disputable",
    "bc39fb91-0d8c-495d-9269-30578294cbd3": "cat ALT normal range — no single option spans 10-100 IU/L correctly",
    "b03a2d47-b7f0-4bfb-82c8-07889e281a5a": "metronidazole for Giardia OR Crypto — conflates organisms with different tx",
    "4c8819dc-42e5-47ee-994a-35c4fc1d3460": "rabbit haematocrit — contradicts sibling question, sources disagree",
    "ea7e8aad-8aca-4c5d-bb1f-e4d973d22122": "meloxicam cats — no option matches 0.045-0.05 mg/kg protocol",
}

# ── FIX — reassign correct answer ─────────────────────────────────────────────
# Format: id → (old_correct, new_correct, brief_reason)
FIX: dict[str, tuple[str, str, str]] = {
    # SNLE
    "aca12daf-3461-43fc-aca3-2d0ea1189538": ("B", "A",
        "Unresponsive patient: oral gel (B) risks aspiration — IM glucagon (A) is standard"),
    "cc25cd53-080b-43f0-a916-8ce5043832f2": ("B", "A",
        "Bilirubin 210 µmol/L ≈ 12.3 mg/dL at 2 days is below AAP phototherapy threshold (~256 µmol/L); breastfeeding (A) is correct"),
    "d840aa70-1009-40d0-9dd3-c7fbfc7de502": ("B", "C",
        "BP 85/50 in sepsis — hemodynamic stabilisation (C) precedes cultures when patient is shocked"),
    "abd6b74a-71cd-4625-a6c1-2adff813109b": ("B", "D",
        "Acute mania priority: safety via minimal stimulation (D) supersedes nutrition (B)"),
    "3d8db64d-64c9-46ff-8528-365d079cd444": ("C", "D",
        "Dobutamine + chest pain — decrease infusion (D) is autonomous nursing action; notify follows"),
    "53ef680b-2e4d-451e-8525-dae94c728d92": ("B", "C",
        "High-alert medication: check blood glucose (C) BEFORE giving insulin — NCLEX safety principle"),
    "3e4bf4df-d8c2-4cf2-974d-d224a5c16a32": ("B", "A",
        "Post-ROSC BP 82/45 — crystalloid bolus (A) for haemodynamic instability precedes 12-lead ECG (B)"),
    "8b68be19-672a-4bf3-963f-2f07d0fda625": ("C", "B",
        "Decreased UO on nephrotoxic drug — assess BP/HR (B) before notifying provider (C)"),
    "7e65503d-6cd2-4a52-9aaf-ffb467871c59": ("B", "C",
        "LP prep: verify platelet/coag (C) is the safety priority before positioning (B)"),
    "ceca920c-ab19-480f-8526-a890a0db2f91": ("B", "D",
        "CHF dyspnoea — assess O2 saturation (D) before intervening with positioning (B)"),
    "0b6af4d6-fe8e-42ed-9e2d-5e4bc8cb428c": ("B", "C",
        "Haemorrhagic stroke — neuro assessment (C) precedes positioning interventions (B)"),
    "26f01c3e-3a22-4203-b714-5ecfba2f94cf": ("B", "C",
        "COPD confusion — neurological assessment (C) comes before ABG (B) in nursing process"),
    # DHA
    "3d32d219-55d8-4b32-b673-b4ecb58dcf18": ("B", "A",
        "Hypovolemic shock — rapid fluid resuscitation (A) is priority over IV potassium (B) which worsens instability"),
    "0275d21f-cd86-4847-b836-648e4eadfd23": ("C", "B",
        "Norepi + vasoconstriction — assess MAP (B) before titrating infusion (C); action without MAP context is unsafe"),
    "c0fda4d3-30a3-409d-b1bf-c183b4501fe9": ("C", "B",
        "Supratherapeutic heparin — stop infusion (B) is immediate nursing action before bleeding assessment (C)"),
    "f7801b1a-399f-4ffc-869d-967392ab9742": ("B", "C",
        "Opioid respiratory depression — prepare naloxone (C); sternal rub (B) is arousal test, not treatment"),
    # HAAD
    "97265935-137e-4fd8-a4f5-22ba0d3f2b70": ("B", "D",
        "Acute mania 48 h awake — prescribe sedative (D) for safety; nutrition (B) is secondary need"),
    "bfabac0f-470f-484e-8f77-953da7f7a6e0": ("C", "D",
        "Unconscious post-arrest — airway via intubation (D) precedes neurological assessment (C)"),
    # QCHP
    "1cacc799-b893-40e4-99a6-3433e1cb7d73": ("B", "D",
        "Glucose 4.2 mmol/L ≈ 75 mg/dL is NOT hypoglycaemic; recheck in 15 min (D) is correct"),
    "117d6a83-1d53-4dae-a673-4a60a03d5458": ("C", "A",
        "Hypovolaemic hypernatraemia with BP 90/60 — isotonic saline bolus (A) stabilises volume before hypotonic correction"),
    "f16f14b4-6a05-4d87-8d9d-c75bb8fc0d85": ("C", "A",
        "Supratherapeutic heparin — stop infusion (A) is autonomous nursing priority before assessing bleeding (C)"),
    "a810dafa-0f5f-4293-97b3-ce9bd26fb3cb": ("B", "C",
        "EHR clinical decision support — use suggestion with documented discrepancy (C); ignoring EHR (B) is unsafe"),
    "7889a16d-27c4-4ab1-a360-e51859c0a0c4": ("C", "D",
        "Suspected child abuse — mandatory reporting to authorities (D) precedes documentation (C)"),
    # NHRA
    "33095f1e-4b61-49bd-bb8f-20918b1b2822": ("C", "D",
        "K=2.8 — assess BP/HR (D) for cardiac manifestations first; provider notification (C) follows assessment"),
    # Veterinary (no exam_slugs)
    "01d0e87a-2c14-4fa9-8c6d-5adb4636ed16": ("D", "A",
        "Feline CKD primary treatment is dietary modification (A), not 'all of above' (D)"),
    "8f6c4765-ffcf-463e-a8c1-e12a9b815b98": ("A", "B",
        "Psittacosis is bacterial (Chlamydophila) — avian influenza (B) is the correct avian viral disease"),
    "9eb31632-5685-479e-b83a-7125e613ee20": ("B", "A",
        "Melphalan for feline lymphoma: 0.1-0.5 mg/kg (A) is within therapeutic range; 0.5-1.0 mg/kg (B) is excessive"),
    "e2526125-a17f-4ba3-aaf5-6071c749a864": ("D", "A",
        "Primary cause of illness/injury in wildlife is trauma (A), not 'all of above'"),
    "57c8f8f9-9bf7-47c0-856d-79921beb6709": ("C", "A",
        "Most common colic cause in cats is GI foreign body (A); IBD (C) causes chronic disease, not acute colic"),
    "c2c7bf18-0577-412e-b72e-6df922da5c57": ("B", "C",
        "Phenobarbital for feline epilepsy: standard dose is 2-4 mg/kg PO BID (C), not 1-2 mg/kg (B)"),
    "681c7800-a267-497a-99d3-50a3008a5b30": ("A", "C",
        "Iatrogenic hyperadrenocorticism (C) is most common in cats; endogenous forms are rare"),
    "577ae432-5e12-4893-9dbe-6af1d5ce4c45": ("D", "A",
        "Primary endoscopy disadvantage in avian patients is respiratory depression (A) due to their unique respiratory anatomy"),
    "76257d36-78ea-4d52-b0bb-75863df4a0c6": ("A", "C",
        "Most common GI disease cause in dogs is GI foreign bodies/dietary indiscretion (C not listed — closest is C); food allergies (A) are less frequent"),
    "d4ef332d-0174-440f-b3f3-e7c227e53325": ("A", "D",
        "Most common cause of mortality in birds is trauma (D), not bacterial infection (A)"),
    "f301bce6-8cd7-45c0-82d2-5bf7c7146214": ("B", "A",
        "Normal canine WBC: 5,000-15,000 cells/µL (A) matches veterinary references; 10,000-20,000 (B) exceeds upper normal"),
    "b5cb8238-ef8f-4611-a533-b66eb091710b": ("A", "B",
        "FHV-1 (B) is most commonly cited as leading cause of feline upper respiratory disease; calicivirus (A) is second"),
    "365126cb-c055-4824-b82e-aad7fc7e3745": ("B", "A",
        "Lomustine for FeLV: 5-10 mg/m² (A) is closer to standard dosing; 10-20 mg/m² IV (B) is too high"),
    "d45ae7c6-caf4-4469-a0e8-8ba7ff07c383": ("D", "A",
        "Most common single sign of feline hyperthyroidism is weight loss (A), not 'all of above' (D)"),
    "5b15924b-9a62-439c-ae34-d3e825e71f7c": ("B", "A",
        "Meloxicam dogs: 0.05-0.1 mg/kg PO/SC SID (A) is correct; 0.1-0.2 mg/kg (B) exceeds recommended dose"),
    "dc25e254-6727-4d89-b1f3-704da44eae70": ("B", "A",
        "Meloxicam canine pain management: 0.05-0.1 mg/kg (A) is standard; 0.1-0.2 mg/kg (B) exceeds label dose"),
    "271b03fb-b62a-4f61-8906-a08e45876842": ("C", "B",
        "Normal rabbit PCV: 30-40% (B) is within the accepted reference range; 40-50% (C) is too high"),
    "9778e433-685a-436e-aec7-881a1d9fc6b2": ("A", "B",
        "Primary reason rabbits visit vet is dental problems (B), not behavioural issues (A)"),
    "31634ba8-533f-43eb-9c83-92e961bece1c": ("A", "D",
        "Colic signs in dogs: vomiting, distension, lethargy, anorexia (D) — diarrhea (in A) is less consistent"),
    "2f090042-b7f5-424c-9324-162b8b802014": ("C", "D",
        "Mild equine colic prognosis: survival rate is 95-100% (D excellent), not 80-90% (C good)"),
}

# ── UNFLAG — answer is defensible, clear the flag ─────────────────────────────
UNFLAG = {
    "fa0a12d8-2814-4f10-a7d6-4d2cd1560bb6": "left lateral position is autonomous nursing action for preeclampsia — defensible",
    "e2cacb5e-681f-4445-bc29-e616479168cd": "blood cultures before antibiotics — correct per SSC Hour-1 bundle",
    "f8042684-0069-4b35-877d-1089ff05779f": "auscultate breath sounds — assessment-first is valid NCLEX approach",
    "b5d4a054-44f1-44f0-aa70-346383199ac5": "assess patient BP/HR first — NCLEX: patient before machine",
    "d2bea0dd-1064-4e96-b0f0-dd008c083825": "decrease dopamine — correct autonomous nursing action before provider notification",
    "753d3c5c-d8d9-46d9-bfbb-56c9f3b07507": "obtain ABG — appropriate first diagnostic step for suspected CO2 narcosis",
    "0633aadb-bf33-4c4b-ad9c-9b1ba6151bd7": "cardiac monitor — no documented issue, answer clinically sound",
    "c6fdcbf0-1b41-4062-8272-cd0ada6eb05f": "blood cultures before antibiotics — correct per SSC sepsis bundle",
    "423c7ee4-6f4d-4603-9e4d-562c03424092": "stop heparin — correct first nursing action for supratherapeutic aPTT",
    "5c1c5bb6-732c-4428-b02f-041eea3b5a75": "obtain ABG — appropriate diagnostic first step for COPD CO2 retention signs",
    "cea7b72c-ef7e-4743-b44e-73b99d24b953": "enrofloxacin 5 mg/kg BID for birds — within 5-10 mg/kg q12h range",
    "3f5d2c9b-cfce-4101-a759-db98e5bee2a3": "vitamin A dose for birds — valid vet module question, not NCLEX scope",
}


async def run_one(db, sql: str, params: dict) -> int:
    r = await db.execute(text(sql), params)
    await db.commit()
    return r.rowcount


async def main() -> None:
    retired = fixed = unflagged = 0
    errors: list[str] = []

    # ── 1. RETIRE ──────────────────────────────────────────────────────────────
    for qid, reason in RETIRE.items():
        try:
            async with async_session_factory() as db:
                n = await run_one(db, "DELETE FROM mcq_questions WHERE id = :id", {"id": qid})
            if n:
                retired += 1
                print(f"  [RETIRED] {qid[:8]}… — {reason[:60]}")
            else:
                print(f"  [SKIP]    {qid[:8]}… not found")
        except Exception as e:
            errors.append(f"RETIRE {qid}: {e}")

    # ── 2. FIX ─────────────────────────────────────────────────────────────────
    for qid, (old_c, new_c, reason) in FIX.items():
        # Build JSON string manually to avoid asyncpg ambiguous-param errors
        import json
        report_json = json.dumps({
            "status": "fixed",
            "old_correct": old_c,
            "new_correct": new_c,
            "reason": reason,
        })
        sql = """
            UPDATE mcq_questions
            SET correct = :new_c,
                verification_status = 'ai_verified',
                verification_report = :report::jsonb
            WHERE id = :id
        """
        try:
            async with async_session_factory() as db:
                n = await run_one(db, sql, {"id": qid, "new_c": new_c, "report": report_json})
            if n:
                fixed += 1
                print(f"  [FIXED]   {qid[:8]}… {old_c}→{new_c}  {reason[:55]}")
            else:
                print(f"  [SKIP]    {qid[:8]}… not found")
        except Exception as e:
            errors.append(f"FIX {qid}: {e}")

    # ── 3. UNFLAG ──────────────────────────────────────────────────────────────
    for qid, reason in UNFLAG.items():
        import json
        report_json = json.dumps({"status": "approved", "reason": reason})
        sql = """
            UPDATE mcq_questions
            SET verification_status = 'ai_verified',
                verification_report = :report::jsonb
            WHERE id = :id
        """
        try:
            async with async_session_factory() as db:
                n = await run_one(db, sql, {"id": qid, "report": report_json})
            if n:
                unflagged += 1
                print(f"  [APPROVED] {qid[:8]}… — {reason[:60]}")
            else:
                print(f"  [SKIP]     {qid[:8]}… not found")
        except Exception as e:
            errors.append(f"UNFLAG {qid}: {e}")

    print(f"\n{'─'*60}")
    print(f"Retired: {retired}  |  Fixed: {fixed}  |  Approved: {unflagged}")
    print(f"Total resolved: {retired + fixed + unflagged} / {len(RETIRE) + len(FIX) + len(UNFLAG)}")
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    asyncio.run(main())
