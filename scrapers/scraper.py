import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import requests

BASE = "https://bulletins.nyu.edu/class-search/api/"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept":  "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://bulletins.nyu.edu/class-search/",
    "Origin":  "https://bulletins.nyu.edu",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type":     "application/x-www-form-urlencoded; charset=UTF-8",
}

# ── School → `coll` filter value (pass directly to API) ────────────────────────
SCHOOL_CODES = {
    "College of Arts and Science":                  "UA,NA",
    "College of Dentistry":                         "CD,UD,ND,DN",
    "Gallatin School of Individualized Study":      "UG,GG",
    "Graduate School of Arts and Sciences":         "GA",
    "Liberal Studies":                              "UF",
    "Long Island School of Medicine":               "ML",
    "Non-School Based Programs - UG":               "UZ",
    "NYU Abu Dhabi":                                "UH,GH,NH",
    "NYU Shanghai":                                 "UI,GI",
    "Robert F. Wagner Graduate School of Public Service": "GP,UW,NP",
    "Rory Meyers College of Nursing":               "GN,UN",
    "School of Global Public Health":               "GU,UU,NU",
    "School of Law":                                "LW,NL",
    "School of Professional Studies":               "GC,UC,CE",
    "Silver School of Social Work":                 "NS,GS,US",
    "Steinhardt School of Culture, Education, and Human Development": "NE,UE,GE",
    "Stern School of Business - Grad":              "GB",
    "Stern School of Business - Undergrad":         "UB",
    "Tandon School of Engineering":                 "GY,UY,GX",
    "Tisch School of the Arts":                     "NT,GT,UT",
}

COMPONENT_MAP = {
    "LEC": "Lecture", "REC": "Recitation", "LAB": "Laboratory",
    "SEM": "Seminar", "STU": "Studio",     "IND": "Independent Study",
    "WKS": "Workshop","CLN": "Clinic",     "FLD": "Field Work",
    "INT": "Internship","RES": "Research", "PRJ": "Project",
    "COL": "Colloquium",
}

STATUS_MAP = {"A": "Open", "C": "Closed", "W": "Waitlist", "X": "Cancelled"}
DAY_MAP    = {"1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu",
              "5": "Fri", "6": "Sat", "7": "Sun", "0": "Sun"}


# ── API helpers ────────────────────────────────────────────────────────────────

def api_post(route: str, query_params: dict, body: dict, retries: int = 3) -> dict:
    url = BASE + "?" + urllib.parse.urlencode({"page": "fose", "route": route, **query_params})
    body_str = urllib.parse.quote(json.dumps(body))
    for attempt in range(retries):
        try:
            r = requests.post(url, headers=HEADERS, data=body_str, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [error] API: {e}", file=sys.stderr)
                return {}
            time.sleep(1 + attempt)
    return {}


def get_filter_data(term_code: str = "9999") -> dict:
    """Returns the full filter schema — subjects, schools, sessions, etc."""
    return api_post("load-filter-data", {}, {"srcdb": term_code})


def search(term_code: str, criteria: list[dict]) -> list[dict]:
    """
    Run a search with any combination of criteria.
    criteria entries: [{"field": "coll", "value": "UA,NA"}, {"field": "subject", "value": "CSCI-UA"}]
    """
    # The URL mirrors criteria as query params (matches what NYU's UI does)
    query_extras = {c["field"]: c["value"] for c in criteria}
    body = {"other": {"srcdb": term_code}, "criteria": criteria}
    return api_post("search", query_extras, body).get("results", [])


def get_class_details(code: str, crn: str, term_code: str) -> dict:
    """
    Fetch full details (description, credits, prereqs) for one class.
    code: "CSCI-UA 101"  crn: "12345"  term_code: "1268"
    """
    body = {
        "group":   f"code:{code}",
        "key":     f"crn:{crn}",
        "srcdb":   term_code,
        "matched": f"crn:{crn},{crn}",
    }
    return api_post("details", {}, body)


# ── Normalization ──────────────────────────────────────────────────────────────

def school_for_coll(coll_suffix: str) -> str:
    """Given 'UA' or 'UA,NA', return the school name."""
    for name, codes in SCHOOL_CODES.items():
        if coll_suffix in codes.split(","):
            return name
    return ""


def school_for_subject(subject_code: str) -> str:
    """Derive school from subject code e.g. 'CSCI-UA' → CAS."""
    if "-" not in subject_code:
        return ""
    suffix = subject_code.split("-")[-1]
    # Handle SHU which is 3 chars
    for name, codes in SCHOOL_CODES.items():
        if suffix in codes.split(","):
            return name
    # Fallback for SHU/others
    if subject_code.endswith("-SHU"):
        return "NYU Shanghai"
    return ""


def split_code(code: str) -> tuple[str, str]:
    """'CSCI-UA 101' → ('CSCI-UA', '101')."""
    m = re.match(r'^([A-Z0-9]+-[A-Z]+)\s+(.+)$', code.strip())
    if m:
        return m.group(1), m.group(2)
    parts = code.rsplit(" ", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (code, "")


def parse_meeting_times(mt_str: str) -> list[dict]:
    if not mt_str:
        return []
    try:
        raw = json.loads(mt_str)
    except Exception:
        return []
    out = []
    for mt in raw:
        day = str(mt.get("meet_day", ""))
        out.append({
            "day":     DAY_MAP.get(day, ""),
            "day_num": int(day) if day.isdigit() else None,
            "start":   format_4digit(mt.get("start_time", "")),
            "end":     format_4digit(mt.get("end_time", "")),
        })
    return out


def format_4digit(t) -> str:
    t = str(t).strip()
    if len(t) == 4 and t.isdigit():
        return f"{t[:2]}:{t[2:]}"
    if len(t) == 3 and t.isdigit():
        return f"0{t[0]}:{t[1:]}"
    return t


def parse_date(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def strip_html(s: str) -> str:
    """Cheap HTML tag stripper for description fields."""
    if not s:
        return ""
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'&nbsp;', ' ', s)
    s = re.sub(r'&amp;', '&', s)
    s = re.sub(r'&lt;', '<', s)
    s = re.sub(r'&gt;', '>', s)
    s = re.sub(r'&quot;', '"', s)
    return s.strip()


def make_id(term_code: str, subject: str, catalog: str, section: str) -> str:
    clean = lambda x: re.sub(r'[^A-Za-z0-9_-]', '', x)
    return f"{clean(term_code)}_{clean(subject)}_{clean(catalog)}_{clean(section)}"


# ── Transform ──────────────────────────────────────────────────────────────────

def result_to_document(r: dict, term_code: str, details: dict = None) -> dict:
    code_full = r.get("code", "")
    subject_code, catalog_number = split_code(code_full)
    section = r.get("no", "")
    status_raw = r.get("stat", "")

    try:
        enrollment = int(r.get("total", 0) or 0)
    except (ValueError, TypeError):
        enrollment = 0

    doc = {
        "_id":            make_id(term_code, subject_code, catalog_number, section),
        "term":           {"code": term_code},
        "school":         school_for_subject(subject_code),
        "subject_code":   subject_code,
        "catalog_number": catalog_number,
        "code":           code_full,
        "title":          r.get("title", "").strip(),
        "section":        section,
        "crn":            r.get("crn", ""),
        "status":         STATUS_MAP.get(status_raw, status_raw),
        "component":      COMPONENT_MAP.get(r.get("schd", ""), r.get("schd", "")),
        "instructor":     r.get("instr", "").strip(),
        "enrollment":     enrollment,
        "start_date":     parse_date(r.get("start_date", "")),
        "end_date":       parse_date(r.get("end_date", "")),
        "meets_human":    r.get("meets", "").strip(),
        "meeting_times":  parse_meeting_times(r.get("meetingTimes", "")),
        "is_cancelled":   bool(r.get("isCancelled", "")) or status_raw == "X",
        "source_key":     r.get("key", ""),
        "scraped_at":     datetime.now(timezone.utc),
    }

    # Enrich with details if provided
    if details:
        doc["description"]   = strip_html(details.get("description", ""))
        doc["credits"]       = details.get("hours", "") or details.get("credits", "")
        doc["prerequisites"] = strip_html(details.get("registration_restrictions", "") or
                                           details.get("prerequisites", ""))
        doc["location"]      = details.get("location", "")
        doc["session"]       = details.get("session", "")
        doc["attributes"]    = details.get("attributes", "")
        doc["notes"]         = strip_html(details.get("notes", ""))
        # Keep the raw details blob for any fields we haven't mapped
        doc["_details_raw"]  = {k: v for k, v in details.items()
                                if k not in ("description", "hours", "credits",
                                             "registration_restrictions", "prerequisites",
                                             "location", "session", "attributes", "notes")}

    return doc


# ── Scrape driver ──────────────────────────────────────────────────────────────

def scrape(
    term_code: str,
    school_filter: Optional[str] = None,
    subject_filter: Optional[str] = None,
    keyword: Optional[str] = None,
    fetch_details: bool = False,
    delay: float = 0.3,
) -> list[dict]:

    # Build criteria list from filters
    criteria = []

    if school_filter:
        match = next((n for n in SCHOOL_CODES if school_filter.lower() in n.lower()), None)
        if not match:
            print(f"[error] No school matching '{school_filter}'", file=sys.stderr)
            print(f"  Available: {list(SCHOOL_CODES.keys())}", file=sys.stderr)
            return []
        criteria.append({"field": "coll", "value": SCHOOL_CODES[match]})
        print(f"🏫 School: {match} (coll={SCHOOL_CODES[match]})", flush=True)

    if subject_filter:
        criteria.append({"field": "subject", "value": subject_filter})
        print(f"📚 Subject: {subject_filter}", flush=True)

    if keyword:
        criteria.append({"field": "keyword", "value": keyword})
        print(f"🔍 Keyword: {keyword}", flush=True)

    if not criteria:
        print("[error] At least one filter required. Use --school, --subject, or --keyword.",
              file=sys.stderr)
        print("  Unfiltered scrapes would be too slow and too many requests.", file=sys.stderr)
        return []

    # One search call — the API supports combined criteria
    print(f"\n⏳ Searching term {term_code}…", flush=True)
    results = search(term_code, criteria)
    print(f"✅ {len(results)} class(es) found", flush=True)

    docs = []
    for i, r in enumerate(results, 1):
        if fetch_details:
            code = r.get("code", "")
            crn  = r.get("crn", "")
            print(f"  [{i}/{len(results)}] {code} — fetching details…", flush=True)
            details = get_class_details(code, crn, term_code)
            docs.append(result_to_document(r, term_code, details))
            time.sleep(delay)
        else:
            docs.append(result_to_document(r, term_code))

    return docs


# ── Output ─────────────────────────────────────────────────────────────────────

class MongoJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return {"$date": o.isoformat()}
        return super().default(o)


def save_json(docs, path, pretty=True):
    with open(path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(docs, f, indent=2, ensure_ascii=False, cls=MongoJSONEncoder)
        else:
            json.dump(docs, f, ensure_ascii=False, cls=MongoJSONEncoder)
    print(f"\n💾 {len(docs)} docs → {path}")


def save_ndjson(docs, path):
    with open(path, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False, cls=MongoJSONEncoder) + "\n")
    print(f"\n💾 {len(docs)} docs → {path}")


def save_to_mongo(docs, mongo_uri, collection="classes"):
    try:
        from pymongo import MongoClient, UpdateOne
    except ImportError:
        print("[error] pip install pymongo", file=sys.stderr)
        sys.exit(1)

    client = MongoClient(mongo_uri)
    db_name = mongo_uri.rsplit("/", 1)[-1].split("?")[0] or "nyu"
    coll = client[db_name][collection]

    coll.create_index("term.code")
    coll.create_index("subject_code")
    coll.create_index("school")
    coll.create_index("crn")
    coll.create_index([("title", "text"), ("code", "text"), ("description", "text")])

    if not docs:
        return
    ops = [UpdateOne({"_id": d["_id"]}, {"$set": d}, upsert=True) for d in docs]
    result = coll.bulk_write(ops, ordered=False)
    print(f"\n💾 MongoDB: {result.upserted_count} new, {result.modified_count} updated")


def save_filter_schema(term_code: str, path: str):
    """Save the full filter schema to JSON — useful for building your app's UI."""
    data = get_filter_data(term_code)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Filter schema → {path}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="NYU Course Scraper — Full Details + MongoDB")
    p.add_argument("--list-schools",   action="store_true")
    p.add_argument("--dump-filters",   help="Save full filter schema to this file (needs --term)")
    p.add_argument("--term",    help="Term code, e.g. 1268")
    p.add_argument("--school",  help="Filter by school (partial match)")
    p.add_argument("--subject", help="Filter by subject code (e.g. CSCI-UA)")
    p.add_argument("--keyword", help="Full-text keyword search")
    p.add_argument("--details", action="store_true",
                   help="Fetch full details (description, credits) for each class")
    p.add_argument("--output",  default="classes.json")
    p.add_argument("--to-mongo",  help="MongoDB URI, e.g. mongodb://localhost:27017/nyu")
    p.add_argument("--collection", default="classes")
    p.add_argument("--delay", type=float, default=0.3)
    args = p.parse_args()

    if args.list_schools:
        print("School → `coll` filter value:")
        for name, code in SCHOOL_CODES.items():
            print(f"  {code:<15}  {name}")
        return

    if args.dump_filters:
        if not args.term:
            print("[error] --dump-filters needs --term", file=sys.stderr)
            sys.exit(1)
        save_filter_schema(args.term, args.dump_filters)
        return

    if not args.term:
        print("[error] --term required", file=sys.stderr)
        sys.exit(1)

    docs = scrape(
        term_code      = args.term,
        school_filter  = args.school,
        subject_filter = args.subject,
        keyword        = args.keyword,
        fetch_details  = args.details,
        delay          = args.delay,
    )

    print(f"\n✅ Total: {len(docs)} classes")

    if args.to_mongo:
        save_to_mongo(docs, args.to_mongo, args.collection)
    elif args.output.endswith(".ndjson"):
        save_ndjson(docs, args.output)
    else:
        save_json(docs, args.output)


if __name__ == "__main__":
    main()
