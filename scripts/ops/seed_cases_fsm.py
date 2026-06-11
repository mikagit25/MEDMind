"""
Generate FSM branching clinical cases for all published modules using Claude.
Each module gets 2 cases: one beginner, one intermediate/advanced.
Cases have 5-7 decision steps with 3 choices each.
Run: python seed_cases_fsm.py [--limit N] [--module CODE]
"""
import asyncio
import json
import re
import sys
import time
import uuid
import argparse
import anthropic
import psycopg2

import os
_db_url = os.environ.get("DATABASE_URL", "postgresql://medmind:medmind_secret@localhost:5434/medmind")
# Strip async driver prefix for psycopg2
DB_DSN = _db_url.replace("postgresql+asyncpg://", "postgresql://")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


CASE_PROMPT = """Medical education expert. Generate a branching clinical case for module "{module_title}" (specialty: {specialty}, difficulty: {difficulty}).

IMPORTANT: Return ONLY compact valid JSON. No markdown. No explanation. Keep all text values SHORT (under 120 chars each).

{{"title":"58yo man with chest pain","presentation":"58yo male presents with 30min crushing chest pain radiating to left arm. Diaphoretic, pale. BP 145/90, HR 95, RR 18, SpO2 97%.","vitals":{{"BP":"145/90","HR":"95","RR":"18","Temp":"37.1","SpO2":"97%"}},"diagnosis":"STEMI","differential_diagnosis":["STEMI","NSTEMI","Aortic dissection"],"management":["Aspirin 325mg","Activate cath lab","IV heparin"],"teaching_points":["Time is muscle in STEMI","Aspirin reduces mortality","Primary PCI over thrombolysis when available"],"max_score":100,"steps":[{{"id":"s1","title":"Initial Assessment","description":"Patient arrives with chest pain. Vitals: BP 145/90, HR 95. What is your first action?","choices":[{{"id":"s1a","text":"12-lead ECG immediately","next_step":"s2","outcome":"Correct — ECG shows ST elevation in V1-V4.","score_delta":20}},{{"id":"s1b","text":"Give nitroglycerin first","next_step":"s2","outcome":"Premature without ECG — could drop BP dangerously.","score_delta":5}},{{"id":"s1c","text":"Order chest X-ray","next_step":"s2","outcome":"Too slow — ECG is the priority.","score_delta":-5}}}]}},{{"id":"s2","title":"ECG Interpretation","description":"ECG shows ST elevation in V1-V4. What is your diagnosis?","choices":[{{"id":"s2a","text":"Anterior STEMI","next_step":"s3","outcome":"Correct! Activate cath lab immediately.","score_delta":25}},{{"id":"s2b","text":"LBBB — not STEMI","next_step":"s3","outcome":"No LBBB present. Re-examine the ECG.","score_delta":-10}},{{"id":"s2c","text":"Pericarditis","next_step":"s3","outcome":"Diffuse ST elevation in pericarditis; here it is regional.","score_delta":0}}}]}},{{"id":"s3","title":"Immediate Management","description":"STEMI confirmed. What do you give NOW?","choices":[{{"id":"s3a","text":"Aspirin + activate cath lab + heparin","next_step":"s4","outcome":"Perfect triple therapy. Door-to-balloon time started.","score_delta":25}},{{"id":"s3b","text":"Thrombolytics only","next_step":"s4","outcome":"Cath lab is available — PCI is superior.","score_delta":5}},{{"id":"s3c","text":"IV fluids and observation","next_step":"s4","outcome":"This patient needs reperfusion now!","score_delta":-15}}}]}},{{"id":"s4","title":"Post-PCI Care","description":"PCI successful. What is the most critical next step?","choices":[{{"id":"s4a","text":"Dual antiplatelet therapy + statin","next_step":null,"outcome":"Excellent — standard post-STEMI care. Patient stable.","score_delta":30}},{{"id":"s4b","text":"Discharge with aspirin only","next_step":null,"outcome":"Needs dual antiplatelet therapy (DAPT) for at least 12 months.","score_delta":5}},{{"id":"s4c","text":"No medications — PCI fixed it","next_step":null,"outcome":"Medications are essential post-PCI.","score_delta":-10}}}]}}],"initial_step_id":"s1","ideal_path":["s1","s2","s3","s4"]}}

Now generate a NEW case for module "{module_title}" (specialty: {specialty}, difficulty: {difficulty}). Same compact JSON format. Different clinical scenario appropriate for this module.
"""

TRANSLATE_PROMPT = """Translate this clinical case JSON from English to {lang_name}.
Keep ALL JSON keys in English. Only translate the VALUES of: title, presentation, description (in steps), text (in choices), outcome (in choices), teaching_points array items, management array items.
Do NOT translate: id, next_step, score_delta, vitals keys (BP/HR/etc), diagnosis, differential_diagnosis.
Return ONLY valid JSON, no markdown.

{case_json}"""

LANGUAGES = {
    "ru": "Russian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "tr": "Turkish",
    "ar": "Arabic",
}


def call_claude(prompt: str, max_tokens: int = 2000) -> str:
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def extract_json(text: str) -> dict:
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def insert_case(conn, module_id: str, case_data: dict, specialty: str, difficulty: str) -> str:
    case_id = str(uuid.uuid4())
    steps = case_data.get("steps", [])
    # Ensure null next_step for terminal steps
    for step in steps:
        for ch in step.get("choices", []):
            if ch.get("next_step") == "null" or ch.get("next_step") == "":
                ch["next_step"] = None

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO clinical_cases
              (id, module_id, title, specialty, presentation, vitals, diagnosis,
               differential_diagnosis, management, teaching_points, difficulty,
               steps, initial_step_id, ideal_path, max_score)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (
            case_id,
            module_id,
            case_data["title"],
            specialty,
            case_data["presentation"],
            json.dumps(case_data.get("vitals", {})),
            case_data.get("diagnosis", ""),
            case_data.get("differential_diagnosis", []),
            case_data.get("management", []),
            case_data.get("teaching_points", []),
            difficulty,
            json.dumps(steps),
            case_data.get("initial_step_id", "step_1"),
            json.dumps(case_data.get("ideal_path", [])),
            case_data.get("max_score", 100),
        ))
    conn.commit()
    return case_id


def insert_translation(conn, case_id: str, locale: str, tr_data: dict):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO clinical_case_translations
              (case_id, locale, title, presentation, teaching_points, management)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (case_id, locale) DO UPDATE
              SET title=EXCLUDED.title, presentation=EXCLUDED.presentation,
                  teaching_points=EXCLUDED.teaching_points, management=EXCLUDED.management
        """, (
            case_id,
            locale,
            tr_data.get("title"),
            tr_data.get("presentation"),
            tr_data.get("teaching_points", []),
            tr_data.get("management", []),
        ))
    conn.commit()


def update_case_steps(conn, case_id: str, steps: list):
    """Update steps with translated content for a locale — stored in main table steps for EN."""
    pass  # Steps translations are part of the case JSON; for other locales stored in translation row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200, help="Max modules to process")
    parser.add_argument("--module", type=str, default=None, help="Process only this module code")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-translate", action="store_true", default=False)
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)

    # Fetch published modules
    with conn.cursor() as cur:
        if args.module:
            cur.execute("""
                SELECT m.id, m.code, COALESCE(m.title_en, m.title) as title, s.name as specialty
                FROM modules m
                LEFT JOIN specialties s ON s.id = m.specialty_id
                WHERE m.is_published = true AND m.code = %s
            """, (args.module,))
        else:
            cur.execute("""
                SELECT m.id, m.code, COALESCE(m.title_en, m.title) as title, s.name as specialty
                FROM modules m
                LEFT JOIN specialties s ON s.id = m.specialty_id
                WHERE m.is_published = true
                ORDER BY m.code
                LIMIT %s
            """, (args.limit,))
        modules = cur.fetchall()

    print(f"Processing {len(modules)} modules...")
    total_created = 0
    total_translated = 0

    for mod_id, mod_code, mod_title, specialty in modules:
        # Check existing cases
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM clinical_cases WHERE module_id = %s", (mod_id,))
            existing = cur.fetchone()[0]

        if args.skip_existing and existing >= 2:
            print(f"  SKIP {mod_code} — already has {existing} cases")
            continue

        print(f"\n→ {mod_code}: {mod_title[:50]}")

        for difficulty in ["beginner", "intermediate"]:
            if existing >= 2:
                break
            if existing >= 1 and difficulty == "beginner":
                print(f"   skip beginner (already has 1 case)")
                existing = 0  # allow intermediate
                continue

            print(f"   generating {difficulty} case...", end=" ", flush=True)
            try:
                prompt = (CASE_PROMPT
                    .replace("{module_title}", mod_title)
                    .replace("{specialty}", specialty or "medicine")
                    .replace("{difficulty}", difficulty)
                )
                raw = call_claude(prompt, max_tokens=4000)
                case_data = extract_json(raw)
                case_id = insert_case(conn, str(mod_id), case_data, specialty or "", difficulty)
                total_created += 1
                print(f"✓ created [{case_id[:8]}]")

                # Translate to all languages
                if not args.no_translate:
                    en_json = json.dumps({
                        "title": case_data["title"],
                        "presentation": case_data["presentation"],
                        "teaching_points": case_data.get("teaching_points", []),
                        "management": case_data.get("management", []),
                    }, ensure_ascii=False)

                    for locale, lang_name in LANGUAGES.items():
                        print(f"     translating → {locale}...", end=" ", flush=True)
                        try:
                            tr_prompt = TRANSLATE_PROMPT.format(lang_name=lang_name, case_json=en_json)
                            tr_raw = call_claude(tr_prompt, max_tokens=1000)
                            tr_data = extract_json(tr_raw)
                            insert_translation(conn, case_id, locale, tr_data)
                            total_translated += 1
                            print("✓")
                            time.sleep(0.3)
                        except Exception as e:
                            print(f"✗ {e}")

                time.sleep(1.0)  # rate limit

            except Exception as e:
                print(f"✗ ERROR: {e}")
                import traceback; traceback.print_exc()
                time.sleep(2)

    conn.close()
    print(f"\n✅ Done. Created {total_created} cases, {total_translated} translations.")


if __name__ == "__main__":
    main()
