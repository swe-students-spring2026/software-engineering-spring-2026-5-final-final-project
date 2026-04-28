"""One-shot script to clear the classes collection and reload from classes_example.json."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
DATA_PATH = Path(__file__).with_name("classes_example.json")


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
    # Normalize status capitalisation
    if "status" in out and isinstance(out["status"], str):
        s = out["status"]
        if s.lower() == "open":
            out["status"] = "Open"
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

    deleted = db.classes.delete_many({}).deleted_count
    print(f"Deleted {deleted} existing class documents.")
    print(f"Loaded {len(raw_docs)} JSON documents; {len(docs)} remain after section-level dedupe.")

    result = db.classes.insert_many(docs, ordered=False)
    print(f"Inserted {len(result.inserted_ids)} class documents.")

    client.close()


if __name__ == "__main__":
    main()
