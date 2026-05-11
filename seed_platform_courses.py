#!/usr/bin/env python3
"""Seed public platform courses using admin user as teacher.
Run: python3 /opt/medmind/seed_platform_courses.py
"""
import uuid, psycopg2

DB = "host=172.18.0.2 port=5432 dbname=medmind user=medmind password=medmind_secret"

COURSES = [
    {
        "title": "Основы кардиологии — ЭКГ и сердечная недостаточность",
        "desc": "Базовый курс по кардиологии: научитесь читать ЭКГ, распознавать и лечить сердечную недостаточность. Подходит студентам и врачам.",
        "emoji": "❤️", "specialty": "Кардиология", "difficulty": "beginner",
        "hours": 4.0, "enrollment_type": "open",
        "module_codes": ["BASE_ECG", "CARDIO_ECG", "CARDIO_HF"],
    },
    {
        "title": "Острый коронарный синдром — от диагностики до реперфузии",
        "desc": "Комплексный курс по ОКС: патофизиология, STEMI vs NSTEMI, тактика лечения и постинфарктная реабилитация.",
        "emoji": "🫀", "specialty": "Кардиология", "difficulty": "intermediate",
        "hours": 5.5, "enrollment_type": "open",
        "module_codes": ["CARDIO_ACS"],
    },
    {
        "title": "Неврология — инсульт и эпилепсия",
        "desc": "Диагностика и ведение острого инсульта, алгоритм TIA, современные подходы к лечению эпилепсии.",
        "emoji": "🧠", "specialty": "Неврология", "difficulty": "intermediate",
        "hours": 4.5, "enrollment_type": "open",
        "module_codes": ["NEURO_STROKE", "NEURO_EPILEPSY"],
    },
    {
        "title": "Иммунология и фармакология — базовый курс",
        "desc": "Основы иммунного ответа, реакции гиперчувствительности, фармакокинетика и ключевые лекарственные взаимодействия.",
        "emoji": "🔬", "specialty": "Базовые науки", "difficulty": "beginner",
        "hours": 3.5, "enrollment_type": "open",
        "module_codes": ["BASE_PATHO_IMMUNO", "BASE_ECG"],
    },
    {
        "title": "Хирургия — неотложные состояния",
        "desc": "Острый живот, политравма, неотложные операции и послеоперационные осложнения — всё что нужно знать дежурному хирургу.",
        "emoji": "🔪", "specialty": "Хирургия", "difficulty": "intermediate",
        "hours": 5.0, "enrollment_type": "open",
        "module_codes": ["SURG_ACUTE", "SURG_TRAUMA"],
    },
    {
        "title": "Дерматология — диагностика кожных болезней",
        "desc": "Морфология высыпаний, псориаз, экзема, дерматомикозы и неотложная дерматология. Практический курс для врачей.",
        "emoji": "🩺", "specialty": "Дерматология", "difficulty": "beginner",
        "hours": 3.0, "enrollment_type": "open",
        "module_codes": ["DERM_BASICS", "DERM_INFECTIONS"],
    },
    {
        "title": "Ветеринария — болезни мелких животных",
        "desc": "Кардиология, нефрология и гастроэнтерология у собак и кошек. Для ветеринарных врачей и студентов.",
        "emoji": "🐾", "specialty": "Ветеринария", "difficulty": "beginner",
        "hours": 4.0, "enrollment_type": "open",
        "module_codes": ["VET_CARDIO_SMALL", "VET_NEPHRO"],
    },
    {
        "title": "Психиатрия — депрессия, тревога и психозы",
        "desc": "Диагностические критерии, современные подходы к фармакотерапии и психосоциальному лечению психических расстройств.",
        "emoji": "🧘", "specialty": "Психиатрия", "difficulty": "beginner",
        "hours": 3.5, "enrollment_type": "open",
        "module_codes": ["PSYCH_MOOD"],
    },
]


def run():
    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    # Get admin user id
    cur.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("No admin user found — run setup first")
        return
    admin_id = row[0]
    print(f"Admin id: {admin_id}")

    # Build module code→id map
    cur.execute("SELECT id, code FROM modules WHERE is_published=true")
    mod_map = {code: mid for mid, code in cur.fetchall()}
    print(f"Found {len(mod_map)} published modules")

    created = 0
    for c in COURSES:
        # Check if course already exists (by title)
        cur.execute("SELECT id FROM courses WHERE title=%s", (c["title"],))
        if cur.fetchone():
            print(f"  [SKIP] {c['title'][:50]}")
            continue

        course_id = str(uuid.uuid4())
        invite_code = uuid.uuid4().hex[:8].upper()

        cur.execute("""
            INSERT INTO courses(id, teacher_id, title, description, invite_code,
                is_public, enrollment_type, difficulty, specialty_tag,
                thumbnail_emoji, estimated_hours, is_active, created_at, updated_at)
            VALUES(%s,%s,%s,%s,%s,true,%s,%s,%s,%s,%s,true,NOW(),NOW())
        """, (course_id, admin_id, c["title"], c["desc"], invite_code,
              c["enrollment_type"], c["difficulty"], c.get("specialty"), c["emoji"],
              c["hours"]))

        # Add modules in order
        order = 0
        for code in c["module_codes"]:
            mid = mod_map.get(code)
            if mid:
                cur.execute("""
                    INSERT INTO course_modules(id, course_id, module_id, module_order, added_at)
                    VALUES(%s,%s,%s,%s,NOW())
                    ON CONFLICT (course_id, module_id) DO NOTHING
                """, (str(uuid.uuid4()), course_id, mid, order))
                order += 1
            else:
                print(f"    [WARN] module '{code}' not found")

        conn.commit()
        print(f"  ✓ Created: {c['title'][:55]} ({order} modules)")
        created += 1

    cur.close()
    conn.close()
    print(f"\n✅ Done! Created {created} platform courses")


if __name__ == "__main__":
    run()
