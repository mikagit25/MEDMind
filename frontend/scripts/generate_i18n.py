#!/usr/bin/env python3
"""
Generate pl.ts and nl.ts locale files from en.ts using Groq with key rotation.

Features:
  - Rotates through all available Groq keys on rate limit / 429
  - Saves progress per section — safe to restart, resumes from last done section
  - Runs indefinitely until all sections are translated (sleeps if all keys exhausted)

Usage:
  python generate_i18n.py --lang pl
  python generate_i18n.py --lang nl
  python generate_i18n.py --lang pl nl
  python generate_i18n.py --lang pl --reset   # clear saved progress and start fresh
"""

import argparse
import json
import os
import re
import time

from groq import Groq

# ── Groq keys loaded from environment (see backend/.env) ──────────────────────
# Set GROQ_API_KEY_3 … GROQ_API_KEY_6, GROQ_KEY_MODULE, GROQ_KEY_MODULE_2,
# GROQ_API_KEY_2, GROQ_API_KEY in the environment before running.
def _env_keys() -> list[str]:
    names = [
        "GROQ_API_KEY_3", "GROQ_API_KEY_4", "GROQ_API_KEY_5", "GROQ_API_KEY_6",
        "GROQ_KEY_MODULE", "GROQ_KEY_MODULE_2", "GROQ_API_KEY_2", "GROQ_API_KEY",
    ]
    return [os.environ[k] for k in names if os.environ.get(k)]

GROQ_KEYS: list[str] = _env_keys()

GROQ_MODEL = "qwen/qwen3.8-27b"

LANG_NAMES = {
    "pl": "Polish",
    "nl": "Dutch (Belgian/Netherlands)",
}

LOCALES_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")
EN_FILE     = os.path.join(LOCALES_DIR, "en.ts")
PROGRESS_DIR = os.path.join(os.path.dirname(__file__), ".i18n_progress")

SYSTEM_PROMPT = """You are a professional UI translator for a medical education platform.
Translate TypeScript locale strings from English into the target language.

Rules:
- Keep ALL keys exactly as-is (do not translate key names)
- Keep TypeScript syntax intact: quotes, commas, brackets, braces, arrays
- Keep template variables unchanged: {n}, {total}, {count}, {{key}}, {{days}}
- Keep HTML tags unchanged: <strong>, etc.
- Keep emoji and icons unchanged
- Keep URL paths unchanged: /articles, /drugs, etc.
- Keep brand names unchanged: MedMind, Claude, PubMed, Groq, Telegram, Stripe, FHIR, USMLE, NCLEX, Anki
- Keep medical abbreviations unchanged: AI, MCQ, CPD, CME, ECG, MRI, CT, XR, SM-2, etc.
- Keep currency unchanged: $0, $15, $40, $299, $199
- For arrays of objects (features, steps, roles, plans, faq), translate all string values inside
- Return ONLY the translated TypeScript code — no markdown fences, no explanation"""


MAX_CHUNK_LINES = 100  # max lines per translated chunk


def _split_body(body: str, max_lines: int = MAX_CHUNK_LINES) -> list[str]:
    """Split a string into chunks of at most max_lines lines.
    Tries to cut at a line ending with  },  or  ],  to avoid mid-object splits."""
    lines = body.splitlines(keepends=True)
    if len(lines) <= max_lines:
        return [body]

    chunks = []
    start = 0
    while start < len(lines):
        end = min(start + max_lines, len(lines))
        if end < len(lines):
            # Look backwards up to 30 lines for a clean boundary
            best = end
            for i in range(end, max(start + max_lines // 2, start), -1):
                s = lines[i - 1].rstrip()
                if s.endswith("},") or s.endswith("],") or s.endswith('",'):
                    best = i
                    break
            end = best
        chunks.append("".join(lines[start:end]))
        start = end
    return chunks


def extract_sections(content: str) -> list[tuple[str, str]]:
    """Split en.ts into named sections; oversized sections become [part N/M] sub-chunks."""
    section_re = re.compile(r"(  // ── .+? ──+)", re.MULTILINE)
    matches = list(section_re.finditer(content))

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        name = m.group(1).strip()
        body = content[start:end]

        sub_chunks = _split_body(body)
        if len(sub_chunks) == 1:
            sections.append((name, body))
        else:
            for ci, chunk in enumerate(sub_chunks):
                sub_name = f"{name} [part {ci+1}/{len(sub_chunks)}]"
                sections.append((sub_name, chunk))

    return sections


def progress_file(lang: str) -> str:
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    return os.path.join(PROGRESS_DIR, f"{lang}.json")


def load_progress(lang: str) -> dict:
    pf = progress_file(lang)
    if os.path.exists(pf):
        with open(pf) as f:
            return json.load(f)
    return {}


def save_progress(lang: str, data: dict):
    with open(progress_file(lang), "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def translate_section(section_body: str, lang: str, key_idx: int) -> tuple[str, int]:
    """
    Translate one section. Rotates keys on rate limit.
    Returns (translated_text, new_key_idx).
    If all keys exhausted, sleeps until reset and retries.
    """
    lang_name = LANG_NAMES[lang]
    prompt = (
        f"Translate the following TypeScript locale section from English to {lang_name}.\n"
        f"Only translate string values — keep all keys, syntax, and special tokens intact.\n\n"
        f"{section_body}"
    )

    exhausted_count = 0

    while True:
        key = GROQ_KEYS[key_idx % len(GROQ_KEYS)]
        client = Groq(api_key=key)
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=8192,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.1,
            )
            result = resp.choices[0].message.content.strip()
            # Strip any markdown fences the model may add
            result = re.sub(r"^```typescript\s*", "", result)
            result = re.sub(r"^```ts\s*",         "", result)
            result = re.sub(r"^```\s*",           "", result)
            result = re.sub(r"\s*```$",           "", result)
            exhausted_count = 0
            return result, key_idx

        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ("rate_limit", "429", "quota", "tokens per")):
                key_idx += 1
                exhausted_count += 1
                if exhausted_count >= len(GROQ_KEYS):
                    # All keys rate-limited — sleep 1h then reset
                    print(f"\n  ⚠ All {len(GROQ_KEYS)} keys exhausted. Sleeping 1 hour before retry...")
                    time.sleep(3600)
                    exhausted_count = 0
                    key_idx = 0
                else:
                    next_key_label = f"key #{(key_idx % len(GROQ_KEYS)) + 1}"
                    print(f" [rate-limit → {next_key_label}]", end="", flush=True)
                    time.sleep(1)
            elif "model_not_found" in err or "404" in err:
                print(f"\n  ✗ Model not found on key #{key_idx % len(GROQ_KEYS) + 1}, trying next...")
                key_idx += 1
                time.sleep(1)
            else:
                print(f"\n  ✗ Unexpected error: {e} — retrying in 5s...")
                time.sleep(5)


def assemble_file(lang: str, translated_sections: dict, section_names: list[str]) -> str:
    lang_name = LANG_NAMES[lang]
    out = f"// {lang_name} — auto-translated from English by Groq AI\n"
    out += f"const {lang} = {{\n"

    seen_base = set()
    for name in section_names:
        # For sub-chunks, only emit the body (no duplicate base section header)
        is_sub = re.search(r"\[part \d+/\d+\]", name)
        base_name = re.sub(r"\s*\[part \d+/\d+\]", "", name) if is_sub else name

        body = translated_sections.get(name, "")
        # Strip any outer const wrapper if model re-added it
        body = re.sub(r"^\s*const \w+ = \{", "", body.strip())
        body = re.sub(r"\}\s*as const;?\s*$", "", body.strip())

        if is_sub:
            # Only add blank line separator before first sub-chunk
            if base_name not in seen_base:
                out += "\n"
                seen_base.add(base_name)
            out += body.rstrip() + "\n"
        else:
            out += body.rstrip() + "\n\n"

    out += "} as const;\n\n"
    out += "// Recursive helper that widens all leaf types to string\n"
    out += "type Widened<T> = T extends string\n"
    out += "  ? string\n"
    out += "  : { [K in keyof T]: Widened<T[K]> };\n\n"
    out += f"export type Translations = Widened<typeof {lang}>;\n"
    out += f"export default {lang};\n"
    return out


def process_lang(lang: str, sections: list[tuple[str, str]], reset: bool):
    lang_name = LANG_NAMES[lang]
    out_file = os.path.join(LOCALES_DIR, f"{lang}.ts")

    progress = {} if reset else load_progress(lang)
    section_names = [name for name, _ in sections]

    todo = [(name, body) for name, body in sections if name not in progress]
    done = len(sections) - len(todo)

    print(f"\n{'='*60}")
    print(f"Translating → {lang_name} ({lang}.ts)")
    print(f"Progress: {done}/{len(sections)} already done")
    print(f"{'='*60}")

    key_idx = 0

    for i, (name, body) in enumerate(todo):
        display = name[:55]
        overall = done + i + 1
        print(f"  [{overall}/{len(sections)}] {display}...", end=" ", flush=True)

        translated, key_idx = translate_section(body, lang, key_idx)
        progress[name] = translated
        save_progress(lang, progress)
        print("✓")
        time.sleep(0.3)

    # Write final file
    out_content = assemble_file(lang, progress, section_names)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(out_content)
    print(f"\n✓ Written: {out_file} ({len(out_content):,} chars)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", nargs="+", choices=list(LANG_NAMES.keys()),
                        default=list(LANG_NAMES.keys()))
    parser.add_argument("--reset", action="store_true",
                        help="Clear saved progress and start fresh")
    args = parser.parse_args()

    with open(EN_FILE, "r", encoding="utf-8") as f:
        en_content = f.read()

    sections = extract_sections(en_content)
    print(f"Found {len(sections)} sections in en.ts")

    for lang in args.lang:
        process_lang(lang, sections, reset=args.reset)

    print("\n✅ All done!")


if __name__ == "__main__":
    main()
