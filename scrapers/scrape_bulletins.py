from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

try:
    from scrapers.bulletins import NYUBulletinScraper, get_mongo_settings, save_programs_to_mongo
except ModuleNotFoundError:
    from bulletins import NYUBulletinScraper, get_mongo_settings, save_programs_to_mongo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape NYU bulletin program requirements into MongoDB or JSON.")
    parser.add_argument("--limit", type=int, default=0, help="Only scrape the first N programs. Use 0 for all.")
    parser.add_argument("--output", help="Optional path to write scraped program data as JSON.")
    parser.add_argument("--to-mongo", action="store_true", help="Upsert scraped program data into MongoDB.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scraper = NYUBulletinScraper()
    docs = scraper.scrape_all_programs(limit=args.limit)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(docs, indent=2, default=_json_default), encoding="utf-8")
        print(f"Saved {len(docs)} program documents to {output_path}")

    if args.to_mongo:
        mongo_uri, mongo_db_name = get_mongo_settings()
        save_programs_to_mongo(docs, mongo_uri, mongo_db_name)
        print(f"Upserted {len(docs)} program documents into MongoDB.")

    if not args.output and not args.to_mongo:
        print(f"Scraped {len(docs)} program documents.")

    return 0


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


if __name__ == "__main__":
    raise SystemExit(main())
