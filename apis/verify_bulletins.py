'''
Script to verify that bulletin programs and requirements are being scraped successfully.
'''

from __future__ import annotations

import argparse
import sys
from typing import Any

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that bulletin programs and requirements are being scraped successfully."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the running API service.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only verify the first N programs. Use 0 to verify all programs.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds for each request.",
    )
    return parser.parse_args()


def fetch_json(url: str, *, params: dict[str, Any] | None, timeout: int) -> Any:
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    try:
        programs = fetch_json(f"{base_url}/programs", params=None, timeout=args.timeout)
    except Exception as exc:
        print(f"Failed to fetch /programs: {exc}", file=sys.stderr)
        return 1

    if not isinstance(programs, list):
        print("Unexpected /programs response: expected a JSON list.", file=sys.stderr)
        return 1

    urls = [program.get("url") for program in programs if isinstance(program, dict) and program.get("url")]
    total_programs = len(urls)
    unique_urls = len(set(urls))

    if args.limit > 0:
        urls = urls[: args.limit]

    failures: list[tuple[str, str]] = []
    empty_requirements: list[str] = []

    for index, url in enumerate(urls, start=1):
        try:
            payload = fetch_json(
                f"{base_url}/program-requirements",
                params={"url": url},
                timeout=args.timeout,
            )
        except Exception as exc:
            failures.append((url, str(exc)))
            continue

        requirements = payload.get("program_requirements", "") if isinstance(payload, dict) else ""
        tables = payload.get("tables", []) if isinstance(payload, dict) else []
        description = payload.get("program_description", "") if isinstance(payload, dict) else ""

        if not requirements and not tables and not description:
            empty_requirements.append(url)

        print(f"[{index}/{len(urls)}] verified {url}")

    print()
    print(f"Programs returned by /programs: {total_programs}")
    print(f"Unique program URLs: {unique_urls}")
    print(f"Programs checked in this run: {len(urls)}")
    print(f"Failed requirement fetches: {len(failures)}")
    print(f"Pages with empty extracted content: {len(empty_requirements)}")

    if unique_urls != total_programs:
        print("Duplicate URLs detected in /programs output.")

    if failures:
        print()
        print("Failures:")
        for url, error in failures[:20]:
            print(f"- {url}")
            print(f"  {error}")

    if empty_requirements:
        print()
        print("Empty extracted content:")
        for url in empty_requirements[:20]:
            print(f"- {url}")

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
