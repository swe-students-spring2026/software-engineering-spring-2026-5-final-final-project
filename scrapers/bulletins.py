from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne


BASE_URL = "https://bulletins.nyu.edu"
PROGRAM_FINDER_URL = f"{BASE_URL}/programs/"
USER_AGENT = "ai-course-selection-assistant/0.1"
COLLECTION_NAME = "program_requirements"
SCHOOL_URL_SEGMENTS = {
    "arts-science": "Arts & Science",
    "arts-and-science": "Arts & Science",
    "college-of-arts-and-science": "Arts & Science",
    "arts": "Tisch",
    "tandon": "Tandon",
    "engineering": "Tandon",
    "culture-education-human-development": "Steinhardt",
    "steinhardt": "Steinhardt",
    "tisch": "Tisch",
    "business": "Stern",
    "stern": "Stern",
    "public-service": "Wagner",
    "wagner": "Wagner",
    "global-public-health": "Global Public Health",
    "liberal-studies": "Liberal Studies",
    "individualized-study": "Gallatin",
    "sps": "SPS",
    "school-of-professional-studies": "SPS",
    "professional-studies": "SPS",
    "abu-dhabi": "Abu Dhabi",
    "shanghai": "Shanghai",
    "nursing": "Rory Meyers",
    "gallatin": "Gallatin",
    "social-work": "Silver",
    "silver": "Silver",
    "dentistry": "Dentistry",
}

# Module-level constants — avoids rebuilding on every call
_KNOWN_SCHOOLS = (
    "Arts & Science",
    "Tandon",
    "Steinhardt",
    "Tisch",
    "Stern",
    "Wagner",
    "Global Public Health",
    "Liberal Studies",
    "SPS",
    "Abu Dhabi",
    "Shanghai",
    "Nursing",
    "Gallatin",
    "Social Work",
    "Dentistry",
)

# Matches "YYYY-YYYY" bulletin year tokens (e.g. "2025-2026")
_BULLETIN_YEAR_RE = re.compile(r"\b(\d{4}-\d{4})\b")

# Use lxml if available — significantly faster than html.parser for large pages
try:
    import lxml  # noqa: F401
    _BS_PARSER = "lxml"
except ImportError:
    _BS_PARSER = "html.parser"


@dataclass(frozen=True)
class BulletinProgram:
    title: str
    url: str
    school: str | None
    award: str | None


class NYUBulletinScraper:
    """Scrape public undergraduate program pages from the NYU Bulletins site."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def get_soup(self, url: str, retries: int = 3, backoff: float = 2.0) -> BeautifulSoup:
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return BeautifulSoup(response.text, _BS_PARSER)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                if attempt == retries - 1:
                    raise
                wait = backoff * (2 ** attempt)
                print(f"  [retry {attempt + 1}/{retries - 1}] {url} — {exc} — waiting {wait:.0f}s")
                time.sleep(wait)
        raise RuntimeError("unreachable")

    def collect_undergraduate_program_links(self) -> list[BulletinProgram]:
        soup = self.get_soup(PROGRAM_FINDER_URL)
        programs: dict[str, BulletinProgram] = {}

        for anchor in soup.select('a[href*="/undergraduate/"][href*="/programs/"]'):
            href = anchor.get("href")
            if not href:
                continue

            full_url = urljoin(BASE_URL, href)
            title = self._clean_text(anchor.get_text(" ", strip=True))
            if not title:
                continue

            award = self._extract_award_from_title(title)
            if award is None:
                continue

            school = self._resolve_school(
                url=full_url,
                text_school=self._extract_school_from_anchor_text(title),
            )
            programs[full_url] = BulletinProgram(
                title=title,
                url=full_url,
                school=school,
                award=award,
            )

        return sorted(programs.values(), key=lambda program: program.title)

    def scrape_program(self, url: str) -> dict[str, Any]:
        soup = self.get_soup(url)
        title_node = soup.select_one("h1")
        title = self._clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
        award = self._extract_award_from_title(title)
        school = self._resolve_school(
            url=url,
            text_school=self._extract_school_from_page(soup),
        )

        return {
            "_id": url,
            "url": url,
            "title": title,
            "school": school,
            "award": award,
            "program_description": self._extract_section_text(
                soup,
                {"Program Description", "Program Overview"},
            ),
            "program_requirements": self._extract_section_text(
                soup,
                {"Program Requirements", "Major Requirements", "Minor Requirements", "Curriculum"},
            ),
            "policies": self._extract_section_text(
                soup,
                {"Policies", "Program Policies"},
            ),
            "tables": self._extract_tables(soup),
            "source": {
                "system": "nyu_bulletins",
                "url": url,
                "bulletin_year": self._extract_bulletin_year(soup),
            },
            "scraped_at": datetime.now(timezone.utc),
        }

    def scrape_all_programs(self, *, limit: int = 0, delay: float = 0.1) -> list[dict[str, Any]]:
        programs = self.collect_undergraduate_program_links()
        if limit > 0:
            programs = programs[:limit]
        docs: list[dict[str, Any]] = []
        for i, program in enumerate(programs):
            print(f"[{i + 1}/{len(programs)}] {program.title}")
            docs.append(self.scrape_program(program.url))
            if i < len(programs) - 1:
                time.sleep(delay)
        return docs

    def _extract_section_text(self, soup: BeautifulSoup, titles: set[str]) -> str:
        for heading in soup.select("h2, h3, h4"):
            heading_text = self._clean_text(heading.get_text(" ", strip=True))
            if heading_text not in titles:
                continue

            chunks: list[str] = []
            sibling = heading.find_next_sibling()
            while sibling is not None and getattr(sibling, "name", None) not in {"h2", "h3", "h4"}:
                if isinstance(sibling, Tag):
                    text = self._clean_text(sibling.get_text(" ", strip=True))
                    if text:
                        chunks.append(text)
                sibling = sibling.find_next_sibling()
            return "\n".join(chunks)

        return ""

    def _extract_tables(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        tables: list[dict[str, Any]] = []
        for table in soup.select("table"):
            rows: list[list[str]] = []
            for row in table.select("tr"):
                # Skip <tfoot> rows — these are footnote/legend rows, not requirements
                if row.find_parent("tfoot") is not None:
                    continue
                cells = [self._cell_text(cell) for cell in row.select("th, td")]
                if not any(cells):
                    continue
                # Skip rows whose first cell is just a bare footnote marker (e.g. "1", "2", "*")
                if re.fullmatch(r"[\d*†‡§¶]{1,3}", cells[0].strip()):
                    continue
                rows.append(cells)
            if not rows:
                continue
            label = self._find_preceding_heading(table)
            tables.append({"label": label, "rows": rows})
        return tables

    def _cell_text(self, cell: Tag) -> str:
        """Extract cell text, stripping footnote superscripts (<sup> with only digits/symbols)."""
        def _parts(node: Any):
            if isinstance(node, NavigableString):
                yield str(node)
            elif isinstance(node, Tag):
                # Drop <sup> elements that are purely footnote markers
                if node.name == "sup" and re.fullmatch(r"[\d*†‡§¶]+", node.get_text(strip=True)):
                    return
                for child in node.children:
                    yield from _parts(child)

        return self._clean_text(" ".join(_parts(cell)))

    def _find_preceding_heading(self, element: Tag) -> str:
        """Return the text of the nearest h2/h3/h4 that precedes this element."""
        node = element.find_previous_sibling()
        while node is not None:
            if isinstance(node, Tag) and node.name in {"h2", "h3", "h4"}:
                return self._clean_text(node.get_text(" ", strip=True))
            node = node.find_previous_sibling()
        # Fall back to the section heading in the parent
        parent = element.parent
        if parent is not None:
            heading = parent.find_previous_sibling(["h2", "h3", "h4"])
            if heading and isinstance(heading, Tag):
                return self._clean_text(heading.get_text(" ", strip=True))
        return ""

    def _extract_award_from_title(self, title: str) -> str | None:
        if "(" not in title or ")" not in title:
            return None
        return title.rsplit("(", 1)[-1].rstrip(")").strip() or None

    def _extract_school_from_anchor_text(self, text: str) -> str | None:
        for school in _KNOWN_SCHOOLS:
            if text.endswith(school):
                return school
        return None

    def _extract_school_from_page(self, soup: BeautifulSoup) -> str | None:
        breadcrumbs = [self._clean_text(node.get_text(" ", strip=True)) for node in soup.select(".breadcrumb li, nav li")]
        for breadcrumb in breadcrumbs:
            school = self._extract_school_from_anchor_text(breadcrumb)
            if school:
                return school
        return None

    def _extract_school_from_url(self, url: str) -> str | None:
        path_parts = [part for part in urlparse(url).path.strip("/").split("/") if part]
        if len(path_parts) < 2:
            return None

        for segment in path_parts:
            school = SCHOOL_URL_SEGMENTS.get(segment.lower())
            if school:
                return school
        return None

    def _resolve_school(self, *, url: str, text_school: str | None) -> str | None:
        url_school = self._extract_school_from_url(url)
        if url_school is not None:
            return url_school
        return text_school

    def _extract_bulletin_year(self, soup: BeautifulSoup) -> str | None:
        # Check high-signal locations first (title, header, nav) before full-page scan
        for selector in ("title", "header", ".site-header", "nav", ".breadcrumb"):
            node = soup.select_one(selector)
            if node:
                m = _BULLETIN_YEAR_RE.search(node.get_text(" ", strip=True))
                if m:
                    return m.group(1)
        # Fall back to full-page scan — still returns on first match
        m = _BULLETIN_YEAR_RE.search(soup.get_text(" ", strip=True))
        return m.group(1) if m else None

    def _clean_text(self, value: str) -> str:
        return " ".join(value.split())


def save_programs_to_mongo(
    docs: list[dict[str, Any]],
    mongo_uri: str,
    db_name: str,
    *,
    collection: str = COLLECTION_NAME,
) -> None:
    client = MongoClient(mongo_uri)
    coll = client[db_name][collection]

    coll.create_index("url", unique=True)
    coll.create_index("title")
    coll.create_index("award")
    coll.create_index("school")
    coll.create_index([("title", "text"), ("program_requirements", "text"), ("program_description", "text")])

    if not docs:
        return

    operations = [UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True) for doc in docs]
    coll.bulk_write(operations, ordered=False)


def load_env() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_mongo_settings() -> tuple[str, str]:
    load_env()
    mongo_uri = os.getenv("MONGO_URI")
    mongo_db_name = os.getenv("MONGO_DB_NAME")
    if not mongo_uri or not mongo_db_name:
        raise RuntimeError("Missing MONGO_URI or MONGO_DB_NAME in the environment or repo root .env.")
    return mongo_uri, mongo_db_name
