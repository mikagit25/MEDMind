#!/usr/bin/env python3
"""Medical image mega-importer v3.
Sources: Wikimedia Commons + OpenI NLM.
Run: nohup python3 /opt/medmind/import_images_v3.py &
     tail -f /tmp/import_v3.log
"""
import json, logging, re, sys, time, uuid, concurrent.futures
from html import unescape
import psycopg2
import requests

DB_DSN = "host=172.18.0.2 port=5432 dbname=medmind user=medmind password=medmind_secret"
COMMONS = "https://commons.wikimedia.org/w/api.php"
OPENI   = "https://openi.nlm.nih.gov/api/search"
VALID_EXT  = {".jpg",".jpeg",".png",".gif",".svg",".webp"}
VALID_MIME = {"image/jpeg","image/png","image/svg+xml","image/gif","image/webp"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler("/tmp/import_v3.log","w")],
)
L = logging.getLogger()

S = requests.Session()
S.headers["User-Agent"] = "MedMind-Educational/3.0 (https://medmind.pro; research.bot@medmind.pro)"

# ─────────────────────── Wikimedia search list ───────────────────────────────
WIKI = [
    # Blausen 3D — massive collection
    ("Blausen anatomy medical", "anatomy","human body","anatomy", 200),
    ("Blausen cardiovascular heart", "anatomy","heart","cardiology", 150),
    ("Blausen nervous system brain", "anatomy","brain","neurology", 150),
    ("Blausen respiratory lung", "anatomy","lung","pulmonology", 100),
    ("Blausen digestive gastrointestinal", "anatomy","abdomen","gastroenterology",100),
    ("Blausen musculoskeletal bone", "anatomy","musculoskeletal","orthopedics",150),
    ("Blausen urogenital kidney", "anatomy","kidney","urology",80),
    ("Blausen endocrine gland", "anatomy","endocrine","endocrinology",80),
    ("Blausen reproductive system", "anatomy","pelvis","gynecology",80),
    ("Blausen immune lymphatic", "anatomy","lymphatic","immunology",60),
    ("Blausen skin integument", "anatomy","skin","dermatology",60),
    ("Blausen eye vision", "anatomy","eye","ophthalmology",60),
    ("Blausen ear hearing", "anatomy","ear","ENT",60),
    ("Blausen cell biology", "anatomy","cell","biology",80),
    ("Blausen blood hematology", "anatomy","blood","hematology",80),
    ("Blausen embryology fetus", "anatomy","embryo","obstetrics",60),
    # X-ray — all specialties
    ("chest X-ray", "xray","chest","radiology",200),
    ("chest radiograph pathology", "xray","chest","pulmonology",200),
    ("pulmonary chest X-ray", "xray","chest","pulmonology",150),
    ("abdominal X-ray bowel obstruction", "xray","abdomen","surgery",100),
    ("spine radiograph vertebral", "xray","spine","orthopedics",150),
    ("bone fracture radiograph", "xray","extremity","orthopedics",200),
    ("hip pelvis radiograph", "xray","pelvis","orthopedics",150),
    ("knee radiograph", "xray","knee","orthopedics",100),
    ("shoulder radiograph humerus", "xray","shoulder","orthopedics",100),
    ("elbow radiograph", "xray","upper extremity","orthopedics",80),
    ("wrist hand radiograph", "xray","upper extremity","orthopedics",150),
    ("foot ankle radiograph", "xray","lower extremity","orthopedics",150),
    ("skull radiograph cranial", "xray","skull","radiology",80),
    ("dental panoramic X-ray", "xray","oral","dentistry",100),
    ("dental periapical X-ray", "xray","oral","dentistry",80),
    ("pediatric chest X-ray", "xray","chest","pediatrics",80),
    ("neonatal chest radiograph", "xray","chest","neonatology",60),
    ("mammography breast", "xray","breast","oncology",100),
    ("cardiac silhouette chest X-ray cardiomegaly", "xray","chest","cardiology",80),
    ("pneumothorax pleural effusion radiograph", "xray","chest","pulmonology",80),
    ("tuberculosis chest radiograph", "xray","chest","infectious disease",80),
    # CT
    ("CT brain head axial", "ct","brain","neurology",200),
    ("CT chest axial", "ct","chest","radiology",150),
    ("CT abdomen axial", "ct","abdomen","radiology",200),
    ("CT spine axial", "ct","spine","radiology",100),
    ("CT pelvis", "ct","pelvis","radiology",100),
    ("CT angiography vessel", "ct","vascular","radiology",100),
    ("CT pulmonary embolism", "ct","chest","pulmonology",80),
    ("CT brain stroke hemorrhage", "ct","brain","neurology",100),
    ("CT liver tumor", "ct","liver","oncology",80),
    ("CT kidney renal", "ct","kidney","nephrology",80),
    ("CT colon colonography", "ct","colon","gastroenterology",60),
    ("cardiac CT coronary", "ct","heart","cardiology",80),
    # MRI
    ("MRI brain axial sagittal", "mri","brain","neurology",200),
    ("MRI brain coronal", "mri","brain","neurology",150),
    ("MRI brain lesion", "mri","brain","neurology",150),
    ("MRI spine cervical", "mri","cervical spine","orthopedics",100),
    ("MRI spine lumbar", "mri","lumbar spine","neurosurgery",100),
    ("MRI spine thoracic", "mri","thoracic spine","neurosurgery",80),
    ("MRI knee joint meniscus", "mri","knee","orthopedics",150),
    ("MRI shoulder rotator cuff", "mri","shoulder","orthopedics",100),
    ("MRI hip joint", "mri","hip","orthopedics",80),
    ("MRI ankle foot", "mri","foot","orthopedics",80),
    ("MRI wrist hand", "mri","wrist","orthopedics",80),
    ("MRI pelvis abdomen", "mri","pelvis","radiology",100),
    ("MRI cardiac heart", "mri","heart","cardiology",80),
    ("MRI breast", "mri","breast","oncology",80),
    ("MRI liver", "mri","liver","gastroenterology",80),
    ("MRI fetal obstetric", "mri","obstetrics","obstetrics",60),
    ("MRI prostate", "mri","prostate","urology",60),
    ("functional MRI brain fMRI", "mri","brain","neuroscience",60),
    # Ultrasound / Echo
    ("ultrasound abdominal", "ultrasound","abdomen","radiology",150),
    ("ultrasound thyroid neck", "ultrasound","neck","endocrinology",80),
    ("ultrasound gallbladder liver", "ultrasound","abdomen","gastroenterology",100),
    ("ultrasound renal kidney", "ultrasound","kidney","nephrology",80),
    ("ultrasound obstetric fetal", "ultrasound","obstetrics","obstetrics",150),
    ("echocardiogram cardiac ultrasound", "ultrasound","heart","cardiology",150),
    ("ultrasound doppler vascular", "ultrasound","vascular","cardiology",100),
    ("ultrasound breast", "ultrasound","breast","radiology",80),
    ("ultrasound musculoskeletal", "ultrasound","musculoskeletal","orthopedics",80),
    ("ultrasound testis scrotal", "ultrasound","pelvis","urology",60),
    ("ultrasound thyroid nodule", "ultrasound","neck","endocrinology",60),
    # Histology / Pathology
    ("histology pathology H&E stain", "histology","tissue","pathology",200),
    ("histology lung pathology", "histology","lung","pathology",100),
    ("histology liver pathology", "histology","liver","pathology",100),
    ("histology kidney pathology", "histology","kidney","pathology",100),
    ("histology heart cardiac pathology", "histology","heart","pathology",80),
    ("histology brain neuropathology", "histology","brain","neuropathology",80),
    ("histology cancer tumor", "histology","tissue","oncology",150),
    ("histology skin dermatopathology", "histology","skin","dermatology",80),
    ("histology colon bowel", "histology","colon","gastroenterology",80),
    ("histology bone marrow", "histology","blood","hematology",80),
    ("histology breast pathology", "histology","breast","oncology",80),
    ("histology prostate", "histology","prostate","urology",60),
    ("histology thyroid", "histology","thyroid","endocrinology",60),
    ("histology lymph node", "histology","lymph node","oncology",80),
    ("histology normal tissue organ", "histology","tissue","pathology",150),
    # Dermatology
    ("skin dermatology lesion rash", "dermatoscopy","skin","dermatology",200),
    ("melanoma skin cancer dermatology", "dermatoscopy","skin","dermatology",100),
    ("psoriasis skin", "dermatoscopy","skin","dermatology",80),
    ("eczema dermatitis", "dermatoscopy","skin","dermatology",80),
    ("acne vulgaris skin", "dermatoscopy","skin","dermatology",60),
    ("urticaria hives skin", "dermatoscopy","skin","dermatology",60),
    ("cellulitis wound infection skin", "dermatoscopy","skin","dermatology",60),
    ("basal cell carcinoma skin", "dermatoscopy","skin","dermatology",60),
    ("vitiligo skin pigmentation", "dermatoscopy","skin","dermatology",60),
    ("herpes zoster rash", "dermatoscopy","skin","infectious disease",60),
    # Ophthalmology
    ("retina fundus eye", "fundoscopy","eye","ophthalmology",200),
    ("diabetic retinopathy fundus", "fundoscopy","eye","ophthalmology",100),
    ("glaucoma optic disc", "fundoscopy","eye","ophthalmology",80),
    ("retinal detachment", "fundoscopy","eye","ophthalmology",60),
    ("macular degeneration retina", "fundoscopy","eye","ophthalmology",60),
    ("cataract eye lens", "fundoscopy","eye","ophthalmology",60),
    ("anterior segment eye slit lamp", "fundoscopy","eye","ophthalmology",80),
    ("cornea eye", "fundoscopy","eye","ophthalmology",60),
    # ECG / Cardiology
    ("ECG electrocardiogram 12 lead", "ecg","heart","cardiology",150),
    ("ECG arrhythmia", "ecg","heart","cardiology",100),
    ("ECG atrial fibrillation flutter", "ecg","heart","cardiology",80),
    ("ECG myocardial infarction STEMI", "ecg","heart","cardiology",80),
    ("ECG bundle branch block", "ecg","heart","cardiology",60),
    ("phonocardiogram heart sounds", "ecg","heart","cardiology",60),
    # Endoscopy
    ("gastroscopy endoscopy stomach", "endoscopy","stomach","gastroenterology",100),
    ("colonoscopy colon endoscopy", "endoscopy","colon","gastroenterology",100),
    ("bronchoscopy airway", "endoscopy","lung","pulmonology",60),
    ("laparoscopy surgical", "endoscopy","abdomen","surgery",80),
    ("arthroscopy joint", "endoscopy","joint","orthopedics",60),
    # Nuclear / PET
    ("PET scan nuclear medicine", "nuclear","whole body","nuclear medicine",80),
    ("bone scan scintigraphy", "nuclear","bone","nuclear medicine",80),
    ("thyroid scintigraphy nuclear", "nuclear","thyroid","endocrinology",60),
    # Pediatrics
    ("pediatric chest X-ray child", "xray","chest","pediatrics",100),
    ("neonatal infant radiograph", "xray","chest","neonatology",80),
    ("pediatric MRI brain child", "mri","brain","pediatrics",80),
    # Neurology
    ("angiography cerebral brain", "ct","brain","neurosurgery",80),
    ("EEG electroencephalogram brain", "ecg","brain","neurology",60),
    # Oncology
    ("tumor cancer imaging", "ct","various","oncology",100),
    ("lymphoma cancer CT MRI", "ct","chest","oncology",80),
    ("bone metastasis radiograph", "xray","bone","oncology",80),
    # Vascular
    ("angiography coronary", "xray","heart","cardiology",80),
    ("angiography peripheral vascular", "xray","vascular","vascular surgery",80),
    ("aortic aneurysm CT", "ct","aorta","vascular surgery",60),
    # Emergency / Trauma
    ("trauma injury radiograph", "xray","extremity","emergency",100),
    ("head trauma CT brain", "ct","brain","emergency",80),
    ("abdominal trauma CT", "ct","abdomen","emergency",60),
]

# ─────────────────────── OpenI NLM search list ───────────────────────────────
OPENI_SEARCHES = [
    ("chest radiograph","xray","chest","radiology",100),
    ("pneumonia consolidation","xray","chest","pulmonology",80),
    ("tuberculosis","xray","chest","infectious disease",60),
    ("pulmonary embolism CT","ct","chest","pulmonology",60),
    ("lung cancer","ct","chest","oncology",80),
    ("brain MRI stroke","mri","brain","neurology",80),
    ("brain hemorrhage CT","ct","brain","neurology",60),
    ("brain tumor glioma MRI","mri","brain","oncology",60),
    ("multiple sclerosis MRI","mri","brain","neurology",60),
    ("spine disc herniation MRI","mri","spine","neurosurgery",60),
    ("knee meniscus tear MRI","mri","knee","orthopedics",60),
    ("osteoporosis bone density","xray","bone","orthopedics",50),
    ("breast cancer mammography","xray","breast","oncology",60),
    ("abdominal CT appendicitis","ct","abdomen","surgery",60),
    ("liver cirrhosis histology","histology","liver","gastroenterology",50),
    ("colon cancer histology","histology","colon","oncology",50),
    ("diabetic retinopathy fundus","fundoscopy","eye","ophthalmology",50),
    ("glaucoma optic nerve","fundoscopy","eye","ophthalmology",50),
    ("skin melanoma dermatoscopy","dermatoscopy","skin","dermatology",60),
    ("echocardiogram cardiac","ultrasound","heart","cardiology",60),
    ("fetal ultrasound obstetric","ultrasound","obstetrics","obstetrics",60),
    ("renal calculi kidney stone CT","ct","kidney","urology",50),
    ("thyroid nodule ultrasound","ultrasound","thyroid","endocrinology",50),
    ("aortic dissection CT","ct","aorta","vascular surgery",50),
    ("atrial fibrillation ECG","ecg","heart","cardiology",50),
    ("STEMI myocardial infarction ECG","ecg","heart","cardiology",50),
    ("gastroscopy endoscopy ulcer","endoscopy","stomach","gastroenterology",50),
    ("PET scan lymphoma","nuclear","chest","oncology",40),
    ("bone scan metastasis","nuclear","bone","oncology",40),
    ("pediatric fracture radiograph","xray","extremity","pediatrics",50),
]


# ─────────────────────── Helpers ─────────────────────────────────────────────

def strip_html(s):
    if not s: return ""
    s = unescape(str(s))
    s = re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",s).strip()[:600]


def clean_title(raw):
    t = raw.replace("File:","").replace("_"," ")
    t = re.sub(r"\.(png|jpg|jpeg|svg|gif|webp)$","",t,flags=re.I)
    t = re.sub(r"^Blausen\s+\d+\s*","",t)
    t = re.sub(r"\s+-\s*[a-z]{2}(-[A-Z]{2})?$","",t)
    return re.sub(r"\s+"," ",t).strip()[:299] or raw[:60]


def is_valid_url(url):
    url_l = url.lower()
    return (any(url_l.endswith(e) for e in VALID_EXT) or
            any(m in url_l for m in ("jpg","jpeg","png","svg","gif")))


def do_insert(cur, rec, existing):
    url = rec.get("image_url","")
    if not url or url in existing:
        return False
    if not is_valid_url(url):
        return False
    existing.add(url)
    try:
        cur.execute("""
            INSERT INTO medical_images
              (id,title,description,modality,anatomy_region,specialty,
               image_url,thumbnail_url,source_name,source_url,license,
               attribution,tags,is_active,view_count,is_user_upload,created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,true,0,false,NOW())
        """, (
            str(uuid.uuid4()),
            rec["title"][:299], rec.get("description","")[:1500],
            rec["modality"], rec.get("anatomy_region"), rec.get("specialty"),
            url, rec.get("thumbnail_url",url),
            rec.get("source_name","Wikimedia Commons"),
            rec.get("source_url"),
            rec.get("license","CC BY-SA 3.0"),
            rec.get("attribution","Wikimedia Commons"),
            json.dumps(rec.get("tags",[])),
        ))
        return True
    except Exception as e:
        L.warning("Insert error: %s", e)
        return False


# ─────────────────────── Wikimedia importer ───────────────────────────────────

def wiki_search(query, offset=0, limit=50):
    try:
        r = S.get(COMMONS, params={
            "action":"query","generator":"search",
            "gsrsearch":f"File: {query}","gsrnamespace":6,
            "gsrlimit":min(limit,50),"gsroffset":offset,
            "prop":"imageinfo","iiprop":"url|mime|extmetadata",
            "iiurlwidth":800,"format":"json",
        }, timeout=25)
        if r.status_code != 200:
            return []
        return list(r.json().get("query",{}).get("pages",{}).values())
    except Exception as e:
        L.warning("Wiki search error %r: %s", query, e)
        return []


def page_to_rec(page, modality, region, specialty, query):
    ii = page.get("imageinfo",[{}])[0]
    url = ii.get("url","")
    if not url: return None
    mime = ii.get("mime","")
    if not (is_valid_url(url) or mime in VALID_MIME): return None

    meta = ii.get("extmetadata",{})
    title = clean_title(page.get("title",""))
    if not title or len(title) < 3: return None

    desc = strip_html(meta.get("ImageDescription",{}).get("value",""))
    if not desc or len(desc) < 8:
        desc = f"Medical {modality} image: {title}. Region: {region}, specialty: {specialty}."

    lic = (meta.get("LicenseShortName",{}).get("value") or
           meta.get("License",{}).get("value") or "CC BY-SA 3.0")
    artist = strip_html(meta.get("Artist",{}).get("value",""))
    if "blausen" in url.lower():
        lic = "CC BY 3.0"; artist = "Blausen Medical Communications Inc."
    elif not artist:
        artist = "Wikimedia Commons contributors"

    fn = url.rsplit("/",1)[-1]
    return {
        "title": title, "description": desc,
        "modality": modality, "anatomy_region": region, "specialty": specialty,
        "image_url": url, "thumbnail_url": ii.get("thumburl") or url,
        "source_name": "Wikimedia Commons",
        "source_url": f"https://commons.wikimedia.org/wiki/File:{fn}",
        "license": lic, "attribution": f"{artist} via Wikimedia Commons",
        "tags": [modality, region, specialty],
    }


def import_wiki(conn):
    cur = conn.cursor()
    cur.execute("SELECT image_url FROM medical_images WHERE is_user_upload=false")
    existing = {r[0] for r in cur.fetchall()}
    L.info("Existing: %d URLs", len(existing))
    total = 0

    for i,(query,mod,region,spec,limit) in enumerate(WIKI, 1):
        L.info("[Wiki %d/%d] %r → %s | limit=%d", i, len(WIKI), query, mod, limit)
        added = offset = 0
        while offset < limit:
            pages = wiki_search(query, offset, min(50, limit-offset))
            if not pages: break
            for p in pages:
                rec = page_to_rec(p, mod, region, spec, query)
                if rec and do_insert(cur, rec, existing):
                    added += 1; total += 1
            conn.commit()
            offset += 50
            time.sleep(0.35)
        L.info("  +%d (total: %d)", added, total)

    return total


# ─────────────────────── OpenI importer ──────────────────────────────────────

def openi_search(query, n=100):
    try:
        r = S.get(OPENI, params={"query":query,"n":min(n,100),"m":1}, timeout=40)
        if r.status_code != 200: return []
        return r.json().get("list",[])
    except Exception as e:
        L.warning("OpenI error %r: %s", query, e)
        return []


def openi_rec(item, modality, region, specialty):
    base = "https://openi.nlm.nih.gov"
    img = item.get("imgLarge","") or item.get("imgSmall","")
    if not img: return None
    url = base + img
    thumb = base + (item.get("imgSmall") or img)

    cap = item.get("caption") or ""
    if isinstance(cap, dict): cap = cap.get("_","") or ""
    cap = cap.strip()
    art_title = (item.get("title") or "").strip()
    abstract = (item.get("abstractText") or "").strip()[:400]

    if cap and len(cap) > 15:
        title = cap[:150]
        desc = cap
        if abstract: desc += f" Source: {abstract[:300]}"
    elif art_title:
        title = art_title[:150]
        desc = art_title
        if abstract: desc += f". {abstract[:400]}"
    else:
        return None

    pmid = str(item.get("uid",""))
    mesh = [m.lower() for m in (item.get("MeSHmajor") or [])[:3]]

    return {
        "title": title[:299], "description": desc[:1200],
        "modality": modality, "anatomy_region": region, "specialty": specialty,
        "image_url": url, "thumbnail_url": thumb,
        "source_name": "Open-i (NLM/NIH)",
        "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
        "license": "Open Access (PMC)",
        "attribution": f"NLM Open-i Medical Image Database. PMID:{pmid}" if pmid else "NLM Open-i",
        "tags": [modality, region] + mesh,
    }


def import_openi(conn):
    cur = conn.cursor()
    cur.execute("SELECT image_url FROM medical_images WHERE is_user_upload=false")
    existing = {r[0] for r in cur.fetchall()}
    total = 0

    for i,(query,mod,region,spec,n) in enumerate(OPENI_SEARCHES, 1):
        L.info("[OpenI %d/%d] %r → %s", i, len(OPENI_SEARCHES), query, mod)
        items = openi_search(query, n)
        added = 0
        for item in items:
            rec = openi_rec(item, mod, region, spec)
            if rec and do_insert(cur, rec, existing):
                added += 1; total += 1
        conn.commit()
        L.info("  +%d (total: %d)", added, total)
        time.sleep(0.8)

    return total


# ─────────────────────── Main ────────────────────────────────────────────────

def main():
    L.info("="*60)
    L.info("MedMind Image Mega-Importer v3")
    L.info("="*60)

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False

    import time as _t
    t0 = _t.time()

    L.info("\n=== PHASE 1: Wikimedia Commons (%d searches) ===", len(WIKI))
    w = import_wiki(conn)
    L.info("Phase 1 done: +%d from Wikimedia", w)

    L.info("\n=== PHASE 2: OpenI NLM (%d searches) ===", len(OPENI_SEARCHES))
    o = import_openi(conn)
    L.info("Phase 2 done: +%d from OpenI NLM", o)

    elapsed = (_t.time() - t0) / 60
    cur = conn.cursor()
    cur.execute("""
        SELECT modality, COUNT(*) FROM medical_images
        WHERE is_user_upload=false GROUP BY modality ORDER BY count DESC
    """)
    cur2 = conn.cursor()
    cur2.execute("SELECT COUNT(*) FROM medical_images WHERE is_user_upload=false")
    total = cur2.fetchone()[0]

    L.info("\n=== FINAL RESULTS (%.1f min) ===", elapsed)
    L.info("Wikimedia: +%d | OpenI: +%d | Grand total in DB: %d", w, o, total)
    for row in cur.fetchall():
        L.info("  %-15s %d", row[0], row[1])

    conn.close()


if __name__ == "__main__":
    main()
