from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from bulletins import NYUBulletinScraper, save_programs_to_mongo
from scraper import find_available_terms, get_mongo_settings, save_to_mongo, scrape_all_schools_for_term

BULLETIN_CLASS_COLLECTION = "bulletin_classes"


def parse_terms() -> list[str]:
    raw_terms = os.getenv("SCRAPER_TERMS", "auto")
    if raw_terms.strip().lower() in {"", "auto", "latest"}:
        terms = find_available_terms(count=2)
        if not terms:
            raise RuntimeError("No available bulletin class-search terms found.")
        print(f"Auto-selected bulletin class-search terms {', '.join(terms)}.", flush=True)
        return terms
    return [term.strip() for term in raw_terms.split(",") if term.strip()]


def parse_interval_seconds() -> int:
    hours = float(os.getenv("SCRAPE_INTERVAL_HOURS", "24"))
    return max(1, int(hours * 3600))


def run_once() -> None:
    mongo_uri, mongo_db_name = get_mongo_settings()

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting daily scrape cycle.", flush=True)

    bulletin_docs = NYUBulletinScraper().scrape_all_programs()
    save_programs_to_mongo(bulletin_docs, mongo_uri, mongo_db_name)
    print(f"Upserted {len(bulletin_docs)} bulletin program documents.", flush=True)

    for term in parse_terms():
        docs = scrape_all_schools_for_term(term, fetch_details=True, delay=0.1)
        save_to_mongo(docs, mongo_uri, BULLETIN_CLASS_COLLECTION, db_name=mongo_db_name)
        print(f"Upserted {len(docs)} bulletin class documents for term {term}.", flush=True)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Daily scrape cycle completed.", flush=True)


def main() -> int:
    interval_seconds = parse_interval_seconds()
    while True:
        run_once()
        print(f"Sleeping for {interval_seconds} seconds before the next scrape cycle.", flush=True)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
