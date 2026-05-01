from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

from bulletins import NYUBulletinScraper, save_programs_to_mongo
from scraper import find_available_terms, get_mongo_settings, save_to_mongo, scrape_all_schools_for_term

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

BULLETIN_CLASS_COLLECTION = "bulletin_classes"


def parse_terms() -> list[str]:
    raw_terms = os.getenv("SCRAPER_TERMS", "auto")
    if raw_terms.strip().lower() in {"", "auto", "latest"}:
        terms = find_available_terms(count=2)
        if not terms:
            raise RuntimeError("No available bulletin class-search terms found.")
        logger.info("Auto-selected bulletin class-search terms: %s", ", ".join(terms))
        return terms
    return [term.strip() for term in raw_terms.split(",") if term.strip()]


def parse_interval_seconds() -> int:
    hours = float(os.getenv("SCRAPE_INTERVAL_HOURS", "24"))
    return max(1, int(hours * 3600))


def run_once() -> None:
    mongo_uri, mongo_db_name = get_mongo_settings()
    errors: list[str] = []

    logger.info("Starting daily scrape cycle.")

    try:
        bulletin_docs = NYUBulletinScraper().scrape_all_programs()
        save_programs_to_mongo(bulletin_docs, mongo_uri, mongo_db_name)
        logger.info("Upserted %d bulletin program documents.", len(bulletin_docs))
    except Exception:
        logger.exception("Bulletin program scrape failed — skipping program requirements update.")
        errors.append("bulletin_programs")

    try:
        terms = parse_terms()
    except Exception:
        logger.exception("Could not determine scrape terms — aborting class scrape.")
        errors.append("term_discovery")
        terms = []

    for term in terms:
        try:
            docs = scrape_all_schools_for_term(term, fetch_details=True, delay=0.1)
            save_to_mongo(docs, mongo_uri, BULLETIN_CLASS_COLLECTION, db_name=mongo_db_name)
            logger.info("Upserted %d bulletin class documents for term %s.", len(docs), term)
        except Exception:
            logger.exception("Bulletin class scrape failed for term %s — continuing with remaining terms.", term)
            errors.append(f"bulletin_classes_{term}")

    if errors:
        logger.warning("Scrape cycle completed with %d error(s): %s", len(errors), ", ".join(errors))
    else:
        logger.info("Daily scrape cycle completed successfully.")


def main() -> int:
    interval_seconds = parse_interval_seconds()
    while True:
        run_once()
        logger.info("Sleeping for %d seconds before the next scrape cycle.", interval_seconds)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
