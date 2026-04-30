"""Load classes_example.json into MongoDB using idempotent upserts.

Replaces the old delete-then-insert approach so there is no downtime window
and partial failures leave the collection in a consistent state.
Also backfills meeting_times from meets_human for older Albert documents
that were scraped before that field was added.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
DATA_PATH = Path(__file__).with_name("classes_example.json")

# ── Meeting-times parser (backfill for Albert docs missing the field) ──────────

_MEETS_RE = re.compile(
    r"^([\w,]+)\s+(\d+)\.(\d+)\s*(AM|PM)\s*-\s*(\d+)\.(\d+)\s*(AM|PM)",
    re.IGNORECASE,
)
_DAY_NUM = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


def _parse_meets_human(meets: str) -> list[dict[str, Any]]:
    if not meets:
        return []
    match = _MEETS_RE.match(meets.strip())
    if not match:
        return []
    days_str, sh, sm, sampm, eh, em, eampm = match.groups()
    sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)
    start_h = sh % 12 + (12 if sampm.upper() == "PM" else 0)
    end_h = eh % 12 + (12 if eampm.upper() == "PM" else 0)
    start = f"{start_h:02d}:{sm:02d}"
    end = f"{end_h:02d}:{em:02d}"
    return [
        {"day": day.strip(), "day_num": _DAY_NUM[day.strip()], "start": start, "end": end}
        for day in days_str.split(",")
        if day.strip() in _DAY_NUM
    ]


# ── Document normalisation ─────────────────────────────────────────────────────

def parse_date(val: object) -> object:
    if isinstance(val, dict) and "$date" in val:
        raw = val["$date"].replace("Z", "+00:00")
        return datetime.fromisoformat(raw)
    return val


def prepare(doc: dict) -> dict:
    out = dict(doc)
    out["term"] = normalize_term(out)
    if is_unit_title(out.get("title", "")):
        out["title"] = ""
    if "scraped_at" in out:
        out["scraped_at"] = parse_date(out["scraped_at"])
    if out.get("status") and str(out["status"]).lower() == "open":
        out["status"] = "Open"
    # Backfill meeting_times for older Albert docs that lack it
    if not out.get("meeting_times") and out.get("meets_human"):
        out["meeting_times"] = _parse_meets_human(out["meets_human"])
    stable_id = make_stable_class_id(out)
    if stable_id:
        out["_id"] = stable_id
    return out


def normalize_term(doc: dict) -> object:
    term = doc.get("term", "")
    if isinstance(term, dict):
        return term
    term_text = str(term or "").strip()
    if re.fullmatch(r"(?:Fall|Spring|Summer|Winter)\s+\d{4}", term_text):
        return term_text

    source_row = (doc.get("source") or {}).get("raw_row", [])
    if isinstance(source_row, list):
        for line in source_row:
            match = re.match(r"^term:\s*((?:Fall|Spring|Summer|Winter)\s+\d{4})$", str(line or "").strip(), re.I)
            if match:
                return match.group(1)

    doc_id = str(doc.get("_id", ""))
    match = re.match(r"^(Fall|Spring|Summer|Winter)(\d{4})_", doc_id)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return term


def is_unit_title(value: object) -> bool:
    return bool(re.match(r"^\|\s*[\d.-]+\s+units?$", str(value or "").strip(), re.I))


def dedupe_docs(docs: list[dict]) -> list[dict]:
    deduped: dict[tuple[Any, ...], dict] = {}
    for doc in docs:
        key = logical_section_key(doc)
        if key not in deduped:
            deduped[key] = doc
    return list(deduped.values())


def logical_section_key(doc: dict) -> tuple[Any, ...]:
    code = clean_token(doc.get("code", ""))
    section = clean_token(doc.get("section", ""))
    crn = clean_token(doc.get("crn", ""))
    if crn:
        return (code, section, crn)
    return (
        term_key(doc),
        code,
        section,
        crn,
    )


def make_stable_class_id(doc: dict) -> str:
    subject = clean_token(doc.get("subject_code", ""))
    catalog = clean_token(doc.get("catalog_number", ""))
    section = clean_section(doc.get("section", ""))

    if not subject or not catalog:
        code_parts = str(doc.get("code", "")).rsplit(" ", 1)
        if len(code_parts) == 2:
            subject = subject or clean_token(code_parts[0])
            catalog = catalog or clean_token(code_parts[1])

    if not subject or not catalog or not section:
        return str(doc.get("_id", ""))

    term = term_id_part(doc)
    parts = [term, subject, catalog, section] if term else [subject, catalog, section]
    return "_".join(part for part in parts if part)


def term_key(doc: dict) -> str:
    term = doc.get("term", "")
    if isinstance(term, dict):
        return clean_token(term.get("code", "") or term.get("name", ""))
    return clean_token(term)


def term_id_part(doc: dict) -> str:
    term = doc.get("term", "")
    if isinstance(term, dict):
        return clean_token(term.get("code", ""))
    return clean_token(term)


def clean_section(value: object) -> str:
    return clean_token(value)


def clean_token(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", str(value or ""))


def main() -> None:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]

    with open(DATA_PATH, encoding="utf-8") as f:
        raw_docs = json.load(f)

    docs = dedupe_docs([prepare(d) for d in raw_docs])
    print(f"Loaded {len(raw_docs)} JSON documents; {len(docs)} remain after section-level dedupe.")

    # Idempotent bulk upsert — no downtime window, safe to re-run
    ops = [UpdateOne({"_id": d["_id"]}, {"$set": d}, upsert=True) for d in docs]
    result = db.classes.bulk_write(ops, ordered=False)
    print(f"Upserted: {result.upserted_count} new, {result.modified_count} updated.")

    client.close()


if __name__ == "__main__":
    main()
