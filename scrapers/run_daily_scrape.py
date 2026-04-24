from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from bulletins import NYUBulletinScraper, get_mongo_settings as get_bulletin_mongo_settings, save_programs_to_mongo
from scraper import get_mongo_settings, save_to_mongo, scrape_all_schools_for_term


def parse_terms() -> list[str]:
    raw_terms = os.getenv("SCRAPER_TERMS", "1268,1266")
    return [term.strip() for term in raw_terms.split(",") if term.strip()]


def parse_interval_seconds() -> int:
    hours = float(os.getenv("SCRAPE_INTERVAL_HOURS", "24"))
    return max(1, int(hours * 3600))


def run_once() -> None:
    mongo_uri, _ = get_mongo_settings()
    _, mongo_db_name = get_bulletin_mongo_settings()

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting daily scrape cycle.", flush=True)

    bulletin_docs = NYUBulletinScraper().scrape_all_programs()
    save_programs_to_mongo(bulletin_docs, mongo_uri, mongo_db_name)
    print(f"Upserted {len(bulletin_docs)} bulletin program documents.", flush=True)

    for term in parse_terms():
        docs = scrape_all_schools_for_term(term, fetch_details=True, delay=0.1)
        save_to_mongo(docs, mongo_uri, "classes")
        print(f"Upserted {len(docs)} class documents for term {term}.", flush=True)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Daily scrape cycle completed.", flush=True)


def main() -> int:
    interval_seconds = parse_interval_seconds()
    while True:
        run_once()
        print(f"Sleeping for {interval_seconds} seconds before the next scrape cycle.", flush=True)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
