#!/usr/bin/env python3
"""Fix untranslated article titles/excerpts where title == English original."""
import json, time, requests, psycopg2, psycopg2.extras
from datetime import datetime

DB_DSN = "host=postgres dbname=medmind user=medmind password=medmind_secret"
LOCALES = ["ru", "de", "ar", "fr", "es", "tr"]

def log(msg): print(f"[{datetime.utcnow():%H:%M:%S}] {msg}", flush=True)

def translate_google(text, target, retries=3):
    if not text or not text.strip(): return text
    for attempt in range(retries):
        try:
            r = requests.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client":"gtx","sl":"en","tl":target,"dt":"t","q":text},
                headers={"User-Agent":"Mozilla/5.0"},
                timeout=25,
            )
            if r.status_code == 200:
                data = r.json()
                result = "".join(seg[0] for seg in data[0] if seg and seg[0])
                time.sleep(0.4)
                return result.strip() or text
            elif r.status_code in (429, 503):
                time.sleep(20 * (attempt+1))
        except Exception as e:
            log(f"  Error: {e}")
            time.sleep(8)
    return text

def main():
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT at2.article_id, at2.locale, a.title as en_title, a.excerpt as en_excerpt,
               at2.title as tr_title, at2.excerpt as tr_excerpt
        FROM article_translations at2
        JOIN articles a ON a.id = at2.article_id
        WHERE at2.title = a.title AND at2.status = 'done'
        ORDER BY at2.locale, a.created_at
    """)
    rows = cur.fetchall()
    log(f"Found {len(rows)} untranslated titles to fix")

    fixed = 0
    for row in rows:
        log(f"  [{row['locale']}] {row['en_title'][:60]}")
        new_title  = translate_google(row['en_title'],  row['locale'])
        new_excerpt = translate_google(row['en_excerpt'], row['locale'])
        cur.execute("""
            UPDATE article_translations SET title=%s, excerpt=%s, updated_at=NOW()
            WHERE article_id=%s AND locale=%s
        """, (new_title, new_excerpt, row['article_id'], row['locale']))
        conn.commit()
        log(f"    → {new_title[:60]}")
        fixed += 1

    cur.close(); conn.close()
    log(f"\n✅ Fixed {fixed} titles")

if __name__ == "__main__": main()
