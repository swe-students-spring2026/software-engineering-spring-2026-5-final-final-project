from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag


BASE_URL = "https://bulletins.nyu.edu"
PROGRAM_FINDER_URL = f"{BASE_URL}/programs/"
USER_AGENT = "ai-course-selection-assistant/0.1"


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

    def get_soup(self, url: str) -> BeautifulSoup:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

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

            school = self._extract_school_from_anchor_text(title)
            programs[full_url] = BulletinProgram(
                title=title,
                url=full_url,
                school=school,
                award=award,
            )

        return sorted(programs.values(), key=lambda program: program.title)

    def scrape_program(self, url: str) -> dict[str, Any]:
        soup = self.get_soup(url)
        title = self._clean_text(soup.select_one("h1").get_text(" ", strip=True)) if soup.select_one("h1") else ""

        return {
            "url": url,
            "title": title,
            "program_description": self._extract_section_text(
                soup,
                {
                    "Program Description",
                    "Program Overview",
                },
            ),
            "program_requirements": self._extract_section_text(
                soup,
                {
                    "Program Requirements",
                    "Major Requirements",
                    "Minor Requirements",
                    "Curriculum",
                },
            ),
            "policies": self._extract_section_text(
                soup,
                {
                    "Policies",
                    "Program Policies",
                },
            ),
            "tables": self._extract_tables(soup),
        }

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

    def _extract_tables(self, soup: BeautifulSoup) -> list[list[list[str]]]:
        tables: list[list[list[str]]] = []
        for table in soup.select("table"):
            rows: list[list[str]] = []
            for row in table.select("tr"):
                cells = [self._clean_text(cell.get_text(" ", strip=True)) for cell in row.select("th, td")]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append(rows)
        return tables

    def _extract_award_from_title(self, title: str) -> str | None:
        if "(" not in title or ")" not in title:
            return None
        return title.rsplit("(", 1)[-1].rstrip(")").strip() or None

    def _extract_school_from_anchor_text(self, text: str) -> str | None:
        known_schools = [
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
        ]
        for school in known_schools:
            if text.endswith(school):
                return school
        return None

    def _clean_text(self, value: str) -> str:
        return " ".join(value.split())
