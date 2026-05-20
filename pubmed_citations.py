"""
PubMed E-utilities integration — бесплатный API NCBI.
Добавляет реальные научные цитаты к каждой статье.

Лимиты: 3 req/sec без ключа, 10 req/sec с API ключом.
Ключ получить: https://www.ncbi.nlm.nih.gov/account/ (бесплатно)
Добавить в .env.prod: NCBI_API_KEY=xxx (опционально)
"""
import logging
import os
import time
import urllib.parse
import urllib.request
import json
import re

log = logging.getLogger(__name__)

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_URL = "https://pubmed.ncbi.nlm.nih.gov"

# Опциональный ключ — без него тоже работает (3 req/sec)
_NCBI_KEY = ""
_env_file = os.path.join(os.path.dirname(__file__), "backend", ".env.prod")
if os.path.exists(_env_file):
    for _line in open(_env_file):
        if _line.startswith("NCBI_API_KEY="):
            _NCBI_KEY = _line.split("=", 1)[1].strip()


def _get(url: str, params: dict, retries: int = 3) -> dict | None:
    if _NCBI_KEY:
        params["api_key"] = _NCBI_KEY
    params["tool"] = "MedMindAI"
    params["email"] = "info@medmind.pro"
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "MedMindAI/1.0 (info@medmind.pro)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                log.debug("PubMed request failed: %s", e)
    return None


def fetch_citations(topic: str, category: str, n: int = 6) -> list[dict]:
    """
    Ищет в PubMed статьи по теме за последние 5 лет.
    Возвращает список dict с ключами: title, authors, journal, year, pmid, doi.
    """
    # Формируем поисковый запрос: тема + медицинские фильтры
    query = f'({topic}[Title/Abstract]) AND ("clinical trial"[pt] OR "review"[pt] OR "guideline"[pt])'

    search_data = _get(ESEARCH, {
        "db": "pubmed",
        "term": query,
        "retmax": n * 2,  # берём с запасом, часть отфильтруем
        "retmode": "json",
        "sort": "relevance",
        "datetype": "pdat",
        "reldate": "1825",  # последние 5 лет
    })
    if not search_data:
        return []

    ids = search_data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        # Fallback — без фильтров
        search_data = _get(ESEARCH, {
            "db": "pubmed",
            "term": topic,
            "retmax": n,
            "retmode": "json",
            "sort": "relevance",
            "datetype": "pdat",
            "reldate": "1825",
        })
        ids = search_data.get("esearchresult", {}).get("idlist", []) if search_data else []

    if not ids:
        return []

    # Получаем метаданные
    time.sleep(0.4)  # уважаем rate limit NCBI
    summary_data = _get(ESUMMARY, {
        "db": "pubmed",
        "id": ",".join(ids[:n]),
        "retmode": "json",
    })
    if not summary_data:
        return []

    citations = []
    for pmid in ids[:n]:
        article = summary_data.get("result", {}).get(pmid, {})
        if not article or article.get("error"):
            continue

        # Авторы
        authors_raw = article.get("authors", [])
        if authors_raw:
            first = authors_raw[0].get("name", "")
            authors_str = f"{first} et al." if len(authors_raw) > 1 else first
        else:
            authors_str = "Anonymous"

        # Журнал и год
        journal = article.get("fulljournalname") or article.get("source", "")
        pub_date = article.get("pubdate", "")
        year = re.search(r"\d{4}", pub_date).group(0) if re.search(r"\d{4}", pub_date) else ""

        # DOI
        article_ids = article.get("articleids", [])
        doi = next((x["value"] for x in article_ids if x.get("idtype") == "doi"), "")

        # Том/страницы
        volume = article.get("volume", "")
        issue = article.get("issue", "")
        pages = article.get("pages", "")
        vol_str = f"{volume}" + (f"({issue})" if issue else "") + (f":{pages}" if pages else "")

        citations.append({
            "pmid": pmid,
            "title": article.get("title", "").rstrip("."),
            "authors": authors_str,
            "journal": journal,
            "year": year,
            "volume": vol_str,
            "doi": doi,
            "url": f"{PUBMED_URL}/{pmid}/",
        })

    return citations


def format_citations_block(citations: list[dict]) -> str:
    """Форматирует список цитат в markdown-секцию References."""
    if not citations:
        return ""
    lines = ["## References\n"]
    for i, c in enumerate(citations, 1):
        ref = f"{i}. {c['authors']}. {c['title']}. *{c['journal']}*."
        if c["year"]:
            ref += f" {c['year']}"
        if c["volume"]:
            ref += f";{c['volume']}"
        ref += f". PMID: [{c['pmid']}]({c['url']})"
        if c["doi"]:
            ref += f". DOI: {c['doi']}"
        ref += "."
        lines.append(ref)
    return "\n".join(lines)


def save_citations_to_db(conn, article_id: str, citations: list[dict]) -> bool:
    """Сохраняет PMIDs и DOIs в поле citations (JSONB) если колонка существует."""
    if not citations:
        return False
    try:
        with conn.cursor() as cur:
            # Проверяем что колонка существует
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='articles' AND column_name='citations'
            """)
            if not cur.fetchone():
                # Создаём колонку если нет
                cur.execute("ALTER TABLE articles ADD COLUMN citations JSONB DEFAULT '[]'::jsonb")
                conn.commit()

            cur.execute(
                "UPDATE articles SET citations=%s::jsonb WHERE id=%s",
                (json.dumps(citations), article_id)
            )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        log.debug("Citations save failed: %s", e)
        return False
