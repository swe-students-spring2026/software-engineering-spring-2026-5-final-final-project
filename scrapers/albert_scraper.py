from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# Pre-compiled regexes used in per-row loops
_COURSE_CODE_RE = re.compile(r"\b[A-Z]{2,5}-[A-Z]{2,3}\s+[A-Z0-9.]+[A-Z]?\b")
_CLEAN_ALBERT_RE = re.compile(r"\b(?:more|less)\s+description\s+for\s+.*$", re.I)
_CLEAN_TOKEN_RE = re.compile(r"[^A-Za-z0-9_-]")
_HEADER_NORMALIZE_RE = re.compile(r"[^a-z0-9& ]+")
_DATES_LINE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}\s*-\s*\d{1,2}/\d{1,2}/\d{4}\b")

# Login-page markers — module-level avoids rebuilding the tuple each call
_LOGIN_MARKERS = (
    "sign in to albert",
    "cookies enabled",
    "login to albert",
    "recaptcha validation",
    "verify that you are not a robot",
)

try:
    import lxml as _lxml  # noqa: F401
    _BS_PARSER = "lxml"
except ImportError:
    _BS_PARSER = "html.parser"

try:
    from scrapers.scraper import make_id, school_for_subject, split_code
except ModuleNotFoundError:
    from scraper import make_id, school_for_subject, split_code


ALBERT_CLASS_SEARCH_URL = "https://sis.nyu.edu/psc/csprod/EMPLOYEE/SA/c/NYU_SR.NYU_CLS_SRCH.GBL"
DEFAULT_OUTPUT = Path(__file__).with_name("classes_example.json")


HEADER_ALIASES = {
    "class nbr": "crn",
    "class number": "crn",
    "class no": "crn",
    "class": "code",
    "course": "code",
    "course number": "code",
    "subject": "subject_code",
    "catalog": "catalog_number",
    "catalog number": "catalog_number",
    "section": "section",
    "component": "component",
    "type": "component",
    "title": "title",
    "course title": "title",
    "description": "title",
    "status": "status",
    "days & times": "meets_human",
    "days and times": "meets_human",
    "meeting pattern": "meets_human",
    "time": "meets_human",
    "instructor": "instructor",
    "instructors": "instructor",
    "room": "location",
    "location": "location",
    "dates": "dates",
    "meeting dates": "dates",
}


class DateTimeJSONEncoder(json.JSONEncoder):
    def default(self, value: object) -> object:
        if isinstance(value, datetime):
            return {"$date": value.isoformat()}
        return super().default(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape visible class-search results from an authenticated NYU Albert session. "
            "Use --interactive-login the first time, then reuse --storage-state, "
            "--browser-profile, or --cdp-url."
        )
    )
    parser.add_argument("--url", default=ALBERT_CLASS_SEARCH_URL)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--report",
        help="Optional path to write a scrape coverage report JSON. Defaults next to --output.",
    )
    parser.add_argument("--html-file", help="Parse a saved Albert results HTML file instead of opening a browser.")
    parser.add_argument("--text-file", help="Parse copied Albert results page text instead of opening a browser.")
    parser.add_argument(
        "--cdp-url",
        help="Attach to an already-running Chromium-based browser via Chrome DevTools Protocol, for example http://127.0.0.1:9222.",
    )
    parser.add_argument("--storage-state", help="Playwright storage_state JSON from a logged-in Albert session.")
    parser.add_argument("--save-storage", help="Write the logged-in browser storage_state JSON here.")
    parser.add_argument(
        "--browser-profile",
        help=(
            "Launch a persistent Chromium-based browser profile directory. "
            "Useful when Albert blocks fresh automation sessions or when you want to reuse an existing logged-in profile."
        ),
    )
    parser.add_argument(
        "--browser-executable",
        help="Path to a Chromium-based browser executable to use with --browser-profile.",
    )
    parser.add_argument("--term", default="", help="Optional term label/code to store on each result.")
    parser.add_argument("--headless", action="store_true", help="Run without a visible browser window.")
    parser.add_argument(
        "--interactive-login",
        action="store_true",
        help="Open a headed browser and wait while you log in and run the desired class search.",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=120000,
        help="How long to wait for Albert/result content after navigation.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional max rows to write. 0 means all rows found.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    report_path = Path(args.report) if args.report else output_path.with_name(output_path.stem + "_report.json")

    if args.html_file or args.text_file:
        if args.html_file:
            source_path = Path(args.html_file)
            rows = extract_rows_from_html(source_path.read_text(encoding="utf-8", errors="replace"))
            source_url = f"file:{source_path.resolve()}"
        else:
            source_path = Path(args.text_file)
            rows = dedupe_rows(extract_rows_from_text(source_path.read_text(encoding="utf-8", errors="replace")))
            source_url = f"file:{source_path.resolve()}"

        docs = rows_to_documents(apply_limit(rows, args.limit), term_code=args.term, source_url=source_url)
        write_docs(output_path, docs)
        print(f"Wrote {len(docs)} Albert class document(s) to {output_path}", flush=True)
        return 0

    with sync_playwright() as playwright:
        browser = None
        attached_browser = None
        context_kwargs: dict[str, Any] = {
            "viewport": {"width": 1440, "height": 1000},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        if args.cdp_url:
            attached_browser = playwright.chromium.connect_over_cdp(args.cdp_url)
            context = ensure_attached_context(attached_browser)
            page = get_or_wait_for_albert_page(context, args.url, args.wait_ms)
        elif args.browser_profile:
            launch_kwargs: dict[str, Any] = {
                "headless": args.headless and not args.interactive_login,
            }
            if args.browser_executable:
                launch_kwargs["executable_path"] = expand_path(args.browser_executable)

            context = playwright.chromium.launch_persistent_context(
                user_data_dir=expand_path(args.browser_profile),
                **launch_kwargs,
                **context_kwargs,
            )
            page = context.new_page()
            page.goto(args.url, wait_until="domcontentloaded", timeout=args.wait_ms)
        else:
            browser = playwright.chromium.launch(headless=args.headless and not args.interactive_login)
            if args.storage_state:
                context_kwargs["storage_state"] = args.storage_state
            context = browser.new_context(**context_kwargs)
            page = context.new_page()
            page.goto(args.url, wait_until="domcontentloaded", timeout=args.wait_ms)

        if args.interactive_login:
            print(
                "Log in to Albert, run the class search you want to capture, "
                "then return here and press Enter.",
                flush=True,
            )
            input()

        if is_login_or_cookie_page(page):
            if attached_browser:
                attached_browser.close()
            else:
                context.close()
            if browser:
                browser.close()
            print(
                "[error] Albert returned a login/cookie page. "
                "Pass reCAPTCHA and log in first, then attach with --cdp-url or use a valid stored session.",
                file=sys.stderr,
            )
            return 1

        existing_docs = load_existing_docs(output_path)
        existing_report = load_existing_report(report_path)
        already_scraped = build_already_scraped_subject_keys(existing_docs, existing_report)
        if already_scraped:
            print(f"Skipping {len(already_scraped)} already-scraped subject(s).", flush=True)

        docs, report = scrape_subject_pages(
            page,
            term_code=args.term,
            wait_ms=args.wait_ms,
            limit=args.limit,
            already_scraped_subject_keys=already_scraped,
        )
        if not docs:
            write_debug_dump(page, output_path)
        write_docs(output_path, docs)
        write_report(report_path, report)

        if args.save_storage:
            context.storage_state(path=args.save_storage)

        if attached_browser:
            attached_browser.close()
        else:
            context.close()
        if browser:
            browser.close()

    print(f"Wrote {len(docs)} Albert class document(s) to {output_path}", flush=True)
    print(
        f"Coverage: {report['visited_subject_count']}/{report['discovered_subject_count']} subjects visited; "
        f"{report['successful_subject_count']} produced classes.",
        flush=True,
    )
    return 0


def apply_limit(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit > 0:
        return rows[:limit]
    return rows


def write_docs(output_path: Path, docs: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing_docs = load_existing_docs(output_path)
    merged_docs = merge_docs_by_id(existing_docs, docs)
    output_path.write_text(
        json.dumps(merged_docs, indent=2, ensure_ascii=False, cls=DateTimeJSONEncoder),
        encoding="utf-8",
    )


def write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def write_debug_dump(page: Any, output_path: Path) -> None:
    debug_path = output_path.with_name(output_path.stem + "_debug.txt")
    parts = [
        f"page_url: {page.url}",
        f"frame_count: {len(page.frames)}",
    ]
    for index, frame in enumerate(iter_accessible_frames(page)):
        text = safe_frame_text(frame)
        if not text:
            continue
        parts.append(f"\n--- frame {index}: {getattr(frame, 'url', '')} ---\n{text[:8000]}")
    debug_path.write_text("\n".join(parts), encoding="utf-8")


def load_existing_docs(output_path: Path) -> list[dict[str, Any]]:
    if not output_path.exists():
        return []
    try:
        raw = json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, list):
        return [doc for doc in raw if isinstance(doc, dict)]
    return []


def load_existing_report(report_path: Path) -> dict[str, Any]:
    if not report_path.exists():
        return {}
    try:
        raw = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def build_already_scraped_subject_keys(
    existing_docs: list[dict[str, Any]],
    existing_report: dict[str, Any] | None = None,
) -> set[str]:
    keys: set[str] = set()

    for doc in existing_docs:
        subject_code = doc.get("subject_code", "")
        if subject_code:
            key = normalize_subject_key(subject_code)
            keys.add(key)
            keys.add(normalize_subject_base_key(key))

    report = existing_report or {}
    for subject in report.get("attempted_subjects", []):
        key = normalize_subject_key(str(subject))
        keys.add(key)
        keys.add(normalize_subject_base_key(key))
    for item in report.get("successful_subjects", []):
        if not isinstance(item, dict):
            continue
        key = normalize_subject_key(str(item.get("subject_key", "") or item.get("label", "")))
        if key:
            keys.add(key)
            keys.add(normalize_subject_base_key(key))

    return {key for key in keys if key}


def merge_docs_by_id(existing_docs: list[dict[str, Any]], new_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = list(existing_docs)
    index_by_id: dict[str, int] = {}
    for idx, doc in enumerate(merged):
        doc_id = str(doc.get("_id", "")).strip()
        if doc_id:
            index_by_id[doc_id] = idx

    for doc in new_docs:
        doc_id = str(doc.get("_id", "")).strip()
        if doc_id and doc_id in index_by_id:
            merged[index_by_id[doc_id]] = doc
        else:
            if doc_id:
                index_by_id[doc_id] = len(merged)
            merged.append(doc)

    return merged


def scrape_subject_pages(
    page: Any,
    *,
    term_code: str,
    wait_ms: int,
    limit: int,
    already_scraped_subject_keys: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_docs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    visited_subjects: set[str] = set(already_scraped_subject_keys or [])
    discovered_subjects: dict[str, str] = {}
    discovered_order: list[str] = []
    attempted_subjects: list[str] = []
    successful_subjects: dict[str, int] = {}
    failed_subjects: list[str] = []
    filter_state = extract_filter_state(page)

    for _ in range(500):
        if is_browse_subject_page(page):
            candidates = get_subject_candidates(page)
            for candidate in candidates:
                key = normalize_subject_key(candidate)
                if key not in discovered_subjects:
                    discovered_subjects[key] = candidate
                    discovered_order.append(key)
        else:
            wait_for_probable_results(page, wait_ms)
            rows = extract_visible_rows(page)
            current_docs = rows_to_documents(rows, term_code=term_code, source_url=page.url)
            before_count = len(all_docs)
            merge_unique_docs(all_docs, current_docs, seen_ids)

            current_subject = infer_subject_key(current_docs, page)
            if current_subject:
                current_subject_key = normalize_subject_key(current_subject)
                visited_subjects.add(current_subject_key)
                if len(all_docs) > before_count:
                    successful_subjects[current_subject_key] = len(all_docs) - before_count

            if limit > 0 and len(all_docs) >= limit:
                return all_docs[:limit], build_report(
                    discovered_subjects,
                    visited_subjects,
                    attempted_subjects,
                    successful_subjects,
                    failed_subjects,
                    all_docs[:limit],
                    filter_state,
                    limited=True,
                )

            if not navigate_to_browse_by_subject(page, wait_ms):
                final_docs = all_docs[:limit] if limit > 0 else all_docs
                return final_docs, build_report(
                    discovered_subjects,
                    visited_subjects,
                    attempted_subjects,
                    successful_subjects,
                    failed_subjects,
                    final_docs,
                    filter_state,
                )

            candidates = get_subject_candidates(page)
            for candidate in candidates:
                key = normalize_subject_key(candidate)
                if key not in discovered_subjects:
                    discovered_subjects[key] = candidate
                    discovered_order.append(key)

        next_subject_key = next(
            (
                key for key in discovered_order
                if key not in visited_subjects and normalize_subject_base_key(key) not in visited_subjects
            ),
            None,
        )
        next_subject = discovered_subjects.get(next_subject_key, "") if next_subject_key else None
        if not next_subject:
            final_docs = all_docs[:limit] if limit > 0 else all_docs
            return final_docs, build_report(
                discovered_subjects,
                visited_subjects,
                attempted_subjects,
                successful_subjects,
                failed_subjects,
                final_docs,
                filter_state,
            )

        print(f"Scraping subject: {next_subject}", flush=True)
        attempted_subjects.append(next_subject)
        if not click_subject_candidate(page, next_subject, wait_ms):
            visited_subjects.add(normalize_subject_key(next_subject))
            failed_subjects.append(next_subject)
            continue

        visited_subjects.add(normalize_subject_key(next_subject))

    final_docs = all_docs[:limit] if limit > 0 else all_docs
    return final_docs, build_report(
        discovered_subjects,
        visited_subjects,
        attempted_subjects,
        successful_subjects,
        failed_subjects,
        final_docs,
        filter_state,
    )


def build_report(
    discovered_subjects: dict[str, str],
    visited_subjects: set[str],
    attempted_subjects: list[str],
    successful_subjects: dict[str, int],
    failed_subjects: list[str],
    docs: list[dict[str, Any]],
    filter_state: dict[str, Any],
    *,
    limited: bool = False,
) -> dict[str, Any]:
    discovered_keys = sorted(discovered_subjects.keys())
    missing_keys = [
        key for key in discovered_keys
        if key not in visited_subjects and normalize_subject_base_key(key) not in visited_subjects
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "limited_run": limited,
        "discovered_subject_count": len(discovered_subjects),
        "visited_subject_count": len(visited_subjects),
        "attempted_subject_count": len(attempted_subjects),
        "successful_subject_count": len(successful_subjects),
        "failed_subject_count": len(failed_subjects),
        "document_count": len(docs),
        "filter_state": filter_state,
        "attempted_subjects": attempted_subjects,
        "successful_subjects": [
            {"subject_key": key, "label": discovered_subjects.get(key, key), "new_documents": successful_subjects[key]}
            for key in sorted(successful_subjects.keys())
        ],
        "failed_subjects": failed_subjects,
        "missing_subjects": [
            {"subject_key": key, "label": discovered_subjects.get(key, key)}
            for key in missing_keys
        ],
    }


def extract_filter_state(page: Any) -> dict[str, Any]:
    for frame in iter_accessible_frames(page):
        try:
            state = frame.evaluate(
                """
                () => {
                  const clean = (text) => (text || '').replace(/\\s+/g, ' ').trim();
                  const labelFor = (el) => {
                    if (!el) return '';
                    if (el.labels && el.labels.length) {
                      return clean(Array.from(el.labels).map(label => label.innerText || label.textContent).join(' '));
                    }
                    const aria = el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('placeholder');
                    if (aria) return clean(aria);
                    const prev = el.previousElementSibling;
                    if (prev) return clean(prev.innerText || prev.textContent);
                    return clean(el.name || el.id || el.type || 'control');
                  };

                  const checkedInputs = Array.from(document.querySelectorAll('input[type=checkbox]:checked, input[type=radio]:checked'))
                    .map(el => ({
                      label: labelFor(el),
                      value: clean(el.value || el.getAttribute('data-label') || 'selected'),
                      name: clean(el.name || ''),
                    }))
                    .filter(item => item.label || item.value);

                  const selectedOptions = Array.from(document.querySelectorAll('select'))
                    .map(el => ({
                      label: labelFor(el),
                      value: clean(el.options[el.selectedIndex]?.text || ''),
                      name: clean(el.name || ''),
                    }))
                    .filter(item => item.value && item.value.toLowerCase() !== ' ');

                  const textInputs = Array.from(document.querySelectorAll('input[type=text], input:not([type]), textarea'))
                    .map(el => ({
                      label: labelFor(el),
                      value: clean(el.value || ''),
                      name: clean(el.name || ''),
                    }))
                    .filter(item => item.value);

                  const bodyText = clean(document.body?.innerText || '');
                  return {
                    page_url: window.location.href,
                    page_title: clean(document.title || ''),
                    checked_inputs: checkedInputs,
                    selected_options: selectedOptions,
                    text_inputs: textInputs,
                    body_preview: bodyText.slice(0, 2000),
                  };
                }
                """
            )
            if state:
                return state
        except Exception:
            continue
    return {}


def merge_unique_docs(existing_docs: list[dict[str, Any]], new_docs: list[dict[str, Any]], seen_ids: set[str]) -> list[dict[str, Any]]:
    for doc in new_docs:
        doc_id = str(doc.get("_id", ""))
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        existing_docs.append(doc)
    return existing_docs


def infer_subject_key(docs: list[dict[str, Any]], page: Any) -> str:
    for doc in docs:
        subject_code = clean_text(doc.get("subject_code", ""))
        if subject_code:
            return subject_code

    text = "\n".join(safe_frame_text(frame) for frame in iter_accessible_frames(page))
    return find_first(r"\b[A-Z]{2,5}-[A-Z]{2,3}\b", text)


def normalize_subject_key(value: str) -> str:
    code = find_first(r"\(([A-Z]{2,5}-[A-Z]{2,3}(?:_[0-9]+)?)\)", value)
    if code:
        return code
    code = find_first(r"\b[A-Z]{2,5}-[A-Z]{2,3}(?:_[0-9]+)?\b", value)
    if code:
        return code
    return clean_text(value).lower()


def normalize_subject_base_key(value: str) -> str:
    return re.sub(r"_\d+$", "", normalize_subject_key(value))


def is_browse_subject_page(page: Any) -> bool:
    text = "\n".join(safe_frame_text(frame) for frame in iter_accessible_frames(page))
    has_subject_list = len(get_subject_candidates(page)) > 10
    has_result_markers = bool(
        re.search(r"class#:\s*\d+", text, re.I)
        or re.search(r"class status:\s*(open|closed|wait)", text, re.I)
        or re.search(r"section:\s*[A-Z0-9]+", text, re.I)
    )
    return has_subject_list and not has_result_markers


def navigate_to_browse_by_subject(page: Any, wait_ms: int) -> bool:
    labels = [
        "Return to Browse by Subject",
        "Browse by Subject",
        "Return",
    ]
    for label in labels:
        if click_control_by_text(page, label):
            wait_for_browse_subjects(page, wait_ms)
            return True

    try:
        page.go_back(wait_until="domcontentloaded", timeout=wait_ms)
        wait_for_browse_subjects(page, wait_ms)
        return True
    except Exception:
        return False


def wait_for_browse_subjects(page: Any, timeout_ms: int) -> None:
    deadline = datetime.now(timezone.utc).timestamp() + (timeout_ms / 1000)
    while datetime.now(timezone.utc).timestamp() < deadline:
        if is_browse_subject_page(page):
            return
        page.wait_for_timeout(250)
    raise PlaywrightTimeoutError("Timed out waiting for the Browse by Subject page to appear.")


def get_subject_candidates(page: Any) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for frame in iter_accessible_frames(page):
        for text in extract_subject_candidates_from_frame(frame):
            if text in seen:
                continue
            seen.add(text)
            candidates.append(text)
    return candidates


def extract_subject_candidates_from_frame(frame: Any) -> list[str]:
    try:
        return frame.evaluate(
            """
            () => {
              const clean = (text) => (text || "").replace(/\\s+/g, " ").trim();
              const skip = /^(return|search|next|previous|class search|browse by subject)$/i;
              const isCandidate = (text) => text && !skip.test(text) && /[A-Z]{2,5}-[A-Z]{2,3}/.test(text);
              const candidates = new Set();
              const selectors = 'a, button, input[type="button"], input[type="submit"], [role="button"]';
              const collect = () => {
                for (const el of Array.from(document.querySelectorAll(selectors))) {
                  const text = clean(el.innerText || el.value || el.textContent);
                  if (isCandidate(text)) {
                    candidates.add(text);
                  }
                }
              };
              const isScrollable = (el) => el && el.scrollHeight > el.clientHeight + 20;
              const scrollables = [
                document.scrollingElement,
                ...Array.from(document.querySelectorAll('*')).filter(isScrollable),
              ].filter(Boolean);
              collect();
              for (const container of scrollables) {
                const start = container.scrollTop;
                const step = Math.max(container.clientHeight * 0.9, 300);
                const maxTop = Math.max(container.scrollHeight - container.clientHeight, 0);
                for (let top = 0; top <= maxTop; top += step) {
                  container.scrollTop = top;
                  collect();
                }
                container.scrollTop = maxTop;
                collect();
                container.scrollTop = start;
              }
              return Array.from(candidates);
            }
            """
        )
    except Exception:
        return []


def click_subject_candidate(page: Any, candidate: str, wait_ms: int) -> bool:
    for frame in iter_accessible_frames(page):
        try:
            clicked = frame.evaluate(
                """
                (targetText) => {
                  const clean = (text) => (text || "").replace(/\\s+/g, " ").trim();
                  for (const el of Array.from(document.querySelectorAll('a, button, input[type="button"], input[type="submit"], [role="button"]'))) {
                    const text = clean(el.innerText || el.value || el.textContent);
                    if (text === targetText) {
                      el.scrollIntoView({block: 'center'});
                      el.click();
                      return true;
                    }
                  }
                  return false;
                }
                """,
                candidate,
            )
            if clicked:
                click_search_control(page)
                wait_for_subject_results(page, wait_ms)
                return True
        except Exception:
            continue
    return False


def wait_for_subject_results(page: Any, timeout_ms: int) -> None:
    for frame in iter_accessible_frames(page):
        try:
            frame.wait_for_function(
                """
                () => {
                  const text = document.body?.innerText || "";
                  return /return to browse by subject/i.test(text)
                    || /class status:/i.test(text)
                    || /visit the bookstore/i.test(text);
                }
                """,
                timeout=timeout_ms,
            )
            return
        except PlaywrightTimeoutError:
            continue
    wait_for_probable_results(page, timeout_ms)


def click_control_by_text(page: Any, label: str) -> bool:
    for frame in iter_accessible_frames(page):
        try:
            clicked = frame.evaluate(
                """
                (targetText) => {
                  const clean = (text) => (text || "").replace(/\\s+/g, " ").trim();
                  const matches = (text, target) => clean(text).toLowerCase() === target.toLowerCase();
                  for (const el of Array.from(document.querySelectorAll('a, button, input[type="button"], input[type="submit"], [role="button"]'))) {
                    const text = clean(el.innerText || el.value || el.textContent);
                    if (matches(text, targetText)) {
                      el.scrollIntoView({block: 'center'});
                      el.click();
                      return true;
                    }
                  }
                  return false;
                }
                """,
                label,
            )
            if clicked:
                return True
        except Exception:
            continue
    return False


def click_search_control(page: Any) -> bool:
    for label in ("Search",):
        if click_control_by_text(page, label):
            return True
    return False


def ensure_attached_context(browser: Any) -> Any:
    if browser.contexts:
        return browser.contexts[0]
    raise RuntimeError("No browser contexts found at the CDP endpoint. Start Brave with --remote-debugging-port first.")


def get_or_wait_for_albert_page(context: Any, url: str, timeout_ms: int) -> Any:
    page = find_albert_page(context, url)
    if page is not None:
        page.bring_to_front()
        return page

    print(
        "Open Albert in the attached browser, pass reCAPTCHA, run the class search, "
        "then press Enter here to let the scraper continue.",
        flush=True,
    )
    input()

    page = find_albert_page(context, url)
    if page is not None:
        page.bring_to_front()
        return page

    deadline = datetime.now(timezone.utc).timestamp() + (timeout_ms / 1000)
    while datetime.now(timezone.utc).timestamp() < deadline:
        page = find_albert_page(context, url)
        if page is not None:
            page.bring_to_front()
            return page

    raise RuntimeError("Could not find an open Albert tab in the attached browser session.")


def find_albert_page(context: Any, url: str) -> Any | None:
    for page in context.pages:
        if is_albert_page(page, url):
            return page
    return None


def expand_path(path: str) -> str:
    return str(Path(os.path.expandvars(os.path.expanduser(path))).resolve())


def is_albert_page(page: Any, url: str) -> bool:
    try:
        current_url = page.url or ""
    except Exception:
        return False
    return "sis.nyu.edu" in current_url or current_url.startswith(url)


def is_login_or_cookie_page(page: Any) -> bool:
    for frame in iter_accessible_frames(page):
        text = safe_frame_text(frame).lower()
        if any(marker in text for marker in _LOGIN_MARKERS):
            return True
    return False


def wait_for_probable_results(page: Any, timeout_ms: int) -> None:
    for frame in iter_accessible_frames(page):
        try:
            frame.wait_for_function(
                """
                () => {
                  const text = document.body?.innerText || "";
                  return /[A-Z]{2,5}-[A-Z]{2,3}\\s+\\d/.test(text)
                    || /class\\s*(nbr|number|no)/i.test(text)
                    || document.querySelectorAll("table tr").length > 3;
                }
                """,
                timeout=timeout_ms,
            )
            return
        except PlaywrightTimeoutError:
            continue


def expand_description_dropdowns(page: Any) -> None:
    expanded_any = False
    for frame in iter_accessible_frames(page):
        try:
            expanded = frame.evaluate(
                """
                () => {
                  const clean = (text) => (text || "").replace(/\\s+/g, " ").trim();
                  const visible = (el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.visibility !== "hidden" && style.display !== "none" && box.width > 0 && box.height > 0;
                  };
                  const expanders = [];
                  const seen = new Set();
                  const controls = document.querySelectorAll('a, button, summary, [role="button"], [aria-expanded], [aria-controls]');
                  for (const el of Array.from(controls)) {
                    if (!visible(el)) continue;
                    if (seen.has(el)) continue;
                    const text = clean(el.innerText || el.textContent || el.getAttribute("aria-label") || "");
                    const ariaExpanded = (el.getAttribute("aria-expanded") || "").toLowerCase();
                    const classText = clean(el.className || "");
                    const looksLikeDescriptionToggle =
                      /more description|show more|expand|view more/i.test(text)
                      || (/description/i.test(text) && /more|show|expand|view/i.test(text))
                      || (/description/i.test(classText) && ariaExpanded !== "true");
                    if (!looksLikeDescriptionToggle) continue;
                    if (ariaExpanded === "true") continue;
                    seen.add(el);
                    expanders.push(el);
                  }

                  for (const el of expanders) {
                    el.scrollIntoView({ block: "center" });
                    el.click();
                  }

                  return expanders.length;
                }
                """
            )
            if expanded:
                expanded_any = True
        except Exception:
            continue

    if expanded_any:
        page.wait_for_timeout(500)


def extract_visible_rows(page: Any) -> list[dict[str, Any]]:
    expand_description_dropdowns(page)
    best_rows: list[dict[str, Any]] = []
    best_score = -1

    for frame in iter_accessible_frames(page):
        table_rows = extract_table_rows_from_frame(frame)
        normalized_rows = [normalize_table_row(row) for row in table_rows]
        normalized_rows = [row for row in normalized_rows if row]
        if normalized_rows and len(normalized_rows) > best_score:
            best_rows = dedupe_rows(normalized_rows)
            best_score = len(best_rows)

    if best_rows:
        return best_rows

    combined_text = "\n".join(safe_frame_text(frame) for frame in iter_accessible_frames(page))
    return dedupe_rows(extract_rows_from_text(combined_text))


def iter_accessible_frames(page: Any) -> list[Any]:
    return list(page.frames)


def safe_frame_text(frame: Any) -> str:
    try:
        return frame.locator("body").inner_text(timeout=5000)
    except Exception:
        return ""


def extract_table_rows_from_frame(frame: Any) -> list[dict[str, Any]]:
    try:
        return frame.evaluate(
            """
            () => {
              const visible = (el) => {
                const style = window.getComputedStyle(el);
                const box = el.getBoundingClientRect();
                return style.visibility !== "hidden" && style.display !== "none" && box.width > 0 && box.height > 0;
              };
              const clean = (text) => (text || "").replace(/\\s+/g, " ").trim();
              const out = [];
              for (const table of Array.from(document.querySelectorAll("table")).filter(visible)) {
                const rows = Array.from(table.querySelectorAll("tr")).filter(visible);
                if (rows.length < 2) continue;
                let headers = [];
                for (const row of rows) {
                  const cells = Array.from(row.querySelectorAll("th,td")).filter(visible).map((cell) => clean(cell.innerText));
                  if (
                    cells.length > 1
                    && cells.some((cell) => /class|course|section|status|instructor/i.test(cell))
                    && !cells.some((cell) => /[A-Z]{2,5}-[A-Z]{2,3}\\s+\\d/.test(cell))
                  ) {
                    headers = cells;
                    continue;
                  }
                  if (headers.length && cells.length >= 2) {
                    out.push({headers, cells});
                  }
                }
              }
              return out;
            }
            """
        )
    except Exception:
        return []


def extract_rows_from_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, _BS_PARSER)
    table_rows: list[dict[str, Any]] = []

    for table in soup.select("table"):
        headers: list[str] = []
        for tr in table.select("tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.select("th, td")]
            cells = [cell for cell in cells if cell]
            if len(cells) < 2:
                continue
            has_heading_cell = bool(tr.select("th"))
            looks_like_header = any(re.search(r"class|course|section|status|instructor", cell, re.I) for cell in cells)
            has_course_code = any(find_course_code(cell) for cell in cells)
            if has_heading_cell or (looks_like_header and not has_course_code):
                headers = cells
                continue
            if headers:
                table_rows.append({"headers": headers, "cells": cells})

    normalized_rows = [normalize_table_row(row) for row in table_rows]
    normalized_rows = [row for row in normalized_rows if row]
    if normalized_rows:
        return dedupe_rows(normalized_rows)

    return dedupe_rows(extract_rows_from_text(soup.get_text("\n", strip=True)))


def normalize_table_row(row: dict[str, Any]) -> dict[str, Any] | None:
    headers = [normalize_header(header) for header in row.get("headers", [])]
    cells = [clean_text(cell) for cell in row.get("cells", [])]
    if not cells or not any(cells):
        return None

    data: dict[str, Any] = {}
    for index, cell in enumerate(cells):
        raw_header = headers[index] if index < len(headers) else f"column_{index + 1}"
        key = HEADER_ALIASES.get(raw_header, raw_header.replace(" ", "_"))
        if cell and key not in data:
            data[key] = cell

    code = find_course_code(" ".join(cells))
    if code and not data.get("code"):
        data["code"] = code

    if not data.get("code") and not data.get("crn") and not data.get("title"):
        return None

    data["source_row"] = cells
    return data


DAY_NUM = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
MEETS_RE = re.compile(
    r"^([\w,]+)\s+(\d+)\.(\d+)\s*(AM|PM)\s*-\s*(\d+)\.(\d+)\s*(AM|PM)",
    re.IGNORECASE,
)


def parse_meets_human(meets: str) -> list[dict[str, Any]]:
    if not meets:
        return []
    match = MEETS_RE.match(meets.strip())
    if not match:
        return []
    days_str, sh, sm, sampm, eh, em, eampm = match.groups()
    sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)
    start_h = sh % 12 + (12 if sampm.upper() == "PM" else 0)
    end_h = eh % 12 + (12 if eampm.upper() == "PM" else 0)
    start = f"{start_h:02d}:{sm:02d}"
    end = f"{end_h:02d}:{em:02d}"
    return [
        {"day": day.strip(), "day_num": DAY_NUM[day.strip()], "start": start, "end": end}
        for day in days_str.split(",")
        if day.strip() in DAY_NUM
    ]


def rows_to_documents(rows: list[dict[str, Any]], *, term_code: str, source_url: str) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    rows = realign_shifted_topic_rows(rows)
    # Tracks the last primary (lecture) record's title/term so secondary sections
    # (recitations, discussions) can inherit them when Albert omits the course header.
    last_primary: dict[str, str] = {"subject_code": "", "catalog_number": "", "title": "", "term": "", "topic": ""}

    for index, row in enumerate(rows, start=1):
        code = sanitize_albert_text(row.get("code", ""))
        subject_code, catalog_number = split_code(code) if code else ("", "")
        if not subject_code and row.get("subject_code"):
            subject_code = sanitize_albert_text(row.get("subject_code", ""))
        if not catalog_number and row.get("catalog_number"):
            catalog_number = sanitize_albert_text(row.get("catalog_number", ""))
        if subject_code and catalog_number and not code:
            code = f"{subject_code} {catalog_number}"

        section = sanitize_albert_text(row.get("section", ""))
        meeting_details = extract_meeting_details(row)
        term = extract_term_label(row, fallback=term_code)
        course_text = extract_course_text(row, code)
        topic = extract_topic(row)
        notes = extract_notes(row)
        prerequisites = extract_prerequisites(notes)
        title = course_text["title"] or sanitize_albert_text(row.get("title", ""))

        # Inherit title/term from the preceding lecture section when this is a
        # secondary section (recitation/discussion) that Albert omits the header for.
        same_course = (subject_code == last_primary["subject_code"] and
                       catalog_number == last_primary["catalog_number"])
        if same_course:
            if not title:
                title = last_primary["title"]
            if not term:
                term = last_primary["term"]
            if not topic:
                topic = last_primary["topic"]

        if title and term:
            last_primary = {
                "subject_code": subject_code,
                "catalog_number": catalog_number,
                "title": title,
                "term": term,
                "topic": topic,
            }

        crn = sanitize_albert_text(row.get("crn", ""))
        doc_id = make_albert_id(
            term,
            subject_code or "unknown",
            catalog_number or str(index),
            section or str(index),
        )

        meets_human = sanitize_albert_text(row.get("meets_human", "")) or meeting_details["meets_human"]
        docs.append(
            {
                "_id": doc_id,
                "term": term,
                "school": school_for_subject(subject_code),
                "subject_code": subject_code,
                "catalog_number": catalog_number,
                "code": code,
                "title": title,
                "topic": topic,
                "description": course_text["description"],
                "section": section,
                "crn": crn,
                "status": sanitize_albert_text(row.get("status", "")),
                "component": extract_component_type(row),
                "instructor": sanitize_albert_text(row.get("instructor", "")) or meeting_details["instructor"],
                "meets_human": meets_human,
                "meeting_times": parse_meets_human(meets_human),
                "location": meeting_details["location"] or sanitize_albert_text(row.get("location", "")),
                "dates": sanitize_albert_text(row.get("dates", "")) or meeting_details["dates"],
                "notes": notes,
                "prerequisites": prerequisites,
                "source": {
                    "system": "nyu_albert",
                    "url": source_url,
                    "raw_row": row.get("source_row", row),
                },
                "scraped_at": datetime.now(timezone.utc),
            }
        )
    return docs


def realign_shifted_topic_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Move a topic line that Albert's text stream attached to the prior section."""
    adjusted: list[dict[str, Any]] = []
    for row in rows:
        copied = dict(row)
        source_row = copied.get("source_row")
        if isinstance(source_row, list):
            copied["source_row"] = list(source_row)
        adjusted.append(copied)

    for index in range(len(adjusted) - 1):
        current = adjusted[index]
        next_row = adjusted[index + 1]
        if clean_text(current.get("code", "")) != clean_text(next_row.get("code", "")):
            continue
        if row_has_topic(next_row):
            continue

        topic_line = trailing_topic_after_bookstore(current)
        if not topic_line:
            continue

        current_source = current.get("source_row")
        if isinstance(current_source, list):
            current_source.pop()

        next_source = next_row.get("source_row")
        if isinstance(next_source, list):
            next_source.insert(0, topic_line)
        elif not next_row.get("topic"):
            next_row["topic"] = topic_from_line(topic_line)

    return adjusted


def row_has_topic(row: dict[str, Any]) -> bool:
    return bool(extract_topic(row))


def trailing_topic_after_bookstore(row: dict[str, Any]) -> str:
    source_row = row.get("source_row", [])
    if not isinstance(source_row, list) or not source_row:
        return ""

    last_line = clean_text(source_row[-1])
    if not topic_from_line(last_line):
        return ""
    if not any(re.match(r"^visit\s+the\s+bookstore\b", clean_text(line), re.I) for line in source_row[:-1]):
        return ""
    return last_line


def topic_from_line(line: str) -> str:
    return sanitize_albert_text(find_first(r"^topic:\s*(.+)$", clean_text(line), flags=re.I))


def make_albert_id(term_code: str, subject: str, catalog: str, section: str) -> str:
    parts = [_CLEAN_TOKEN_RE.sub("", str(v or "")) for v in (term_code, subject, catalog, section)]
    parts = [part for part in parts if part]
    return "_".join(parts)


def extract_component_type(row: dict[str, Any]) -> str:
    source_row = row.get("source_row", [])
    if isinstance(source_row, list):
        for line in source_row:
            comp = find_first(r"^component:\s*(.+)$", clean_text(line), flags=re.I)
            if comp:
                return sanitize_albert_text(comp)
    return sanitize_albert_text(row.get("component", ""))


def extract_notes(row: dict[str, Any]) -> str:
    source_row = row.get("source_row", [])
    notes: list[str] = []

    if isinstance(source_row, list):
        for line in source_row:
            text = sanitize_albert_text(line)
            if not text.lower().startswith("notes:"):
                continue
            note = sanitize_albert_text(re.sub(r"^notes:\s*", "", text, flags=re.I))
            if note:
                notes.append(note)

    if not notes and row.get("notes"):
        notes.append(sanitize_albert_text(row.get("notes", "")))

    return sanitize_albert_text(" ".join(notes))


def extract_prerequisites(notes: str) -> str:
    notes = sanitize_albert_text(notes)
    if not notes:
        return ""
    if not re.search(r"\b(?:pre[-\s]?requisite|prereq|prerequisites?)\b", notes, flags=re.I):
        return ""
    return notes


def sanitize_albert_text(value: object) -> str:
    text = clean_text(value)
    text = _CLEAN_ALBERT_RE.sub("", text)
    return clean_text(text)


def extract_term_label(row: dict[str, Any], *, fallback: str = "") -> str:
    source_row = row.get("source_row", [])
    if isinstance(source_row, list):
        for line in source_row:
            text = clean_text(line)
            term = find_first(r"^term:\s*(.+)$", text, flags=re.I)
            if term:
                return sanitize_albert_text(term)
    return sanitize_albert_text(fallback)


def extract_topic(row: dict[str, Any]) -> str:
    source_row = row.get("source_row", [])
    if isinstance(source_row, list):
        for line in reversed(source_row):
            text = clean_text(line)
            topic = topic_from_line(text)
            if topic:
                return topic
    return sanitize_albert_text(row.get("topic", ""))


def extract_course_text(row: dict[str, Any], code: str) -> dict[str, str]:
    details = {
        "title": "",
        "description": "",
    }
    source_row = row.get("source_row", [])
    if not isinstance(source_row, list) or not code:
        return details

    header_index = -1
    for index, line in enumerate(source_row):
        text = sanitize_albert_text(line)
        if not text.startswith(code):
            continue
        remainder = sanitize_albert_text(text[len(code) :])
        if not remainder or re.match(r"^\|\s*[\d.-]+\s+units?$", remainder, re.I):
            continue
        details["title"] = remainder
        header_index = index
        break

    if header_index >= 0:
        description_lines: list[str] = []
        stop_markers = (
            "school:",
            "term:",
            "class#:",
            "section:",
            "class status:",
            "grading:",
            "instruction mode:",
            "course location:",
            "session:",
            "component:",
            "notes:",
            "visit the bookstore",
        )
        for line in source_row[header_index + 1 :]:
            text = sanitize_albert_text(line)
            lower = text.lower()
            if not text:
                continue
            if text.startswith(code):
                break
            if any(lower.startswith(marker) for marker in stop_markers):
                break
            description_lines.append(text)
        details["description"] = sanitize_albert_text(" ".join(description_lines))

    return details


def extract_meeting_details(row: dict[str, Any]) -> dict[str, str]:
    details = {
        "dates": "",
        "meets_human": "",
        "location": "",
        "instructor": "",
    }
    source_row = row.get("source_row", [])
    if not isinstance(source_row, list):
        return details

    for line in source_row:
        text = clean_text(line)
        if not text:
            continue
        if not _DATES_LINE_RE.match(text):
            continue

        details["dates"] = find_first(
            r"^(\d{1,2}/\d{1,2}/\d{4}\s*-\s*\d{1,2}/\d{1,2}/\d{4})",
            text,
        )

        after_dates = text[len(details["dates"]) :].strip() if details["dates"] else text
        instructor = find_first(r"\bwith\s+(.+)$", after_dates, flags=re.I)
        if instructor:
            details["instructor"] = instructor
            after_dates = re.sub(r"\bwith\s+.+$", "", after_dates, flags=re.I).strip()

        location = find_first(r"\bat\s+(.+)$", after_dates, flags=re.I)
        if location:
            details["location"] = location
            after_dates = re.sub(r"\bat\s+.+$", "", after_dates, flags=re.I).strip()

        details["meets_human"] = after_dates
        break

    # Fall back to the Notes line: "Notes: Fall 2026 Instructor: NAME Fall 2026 ..."
    if not details["instructor"]:
        for line in source_row:
            text = clean_text(line)
            if not text.lower().startswith("notes:"):
                continue
            instr = find_first(
                r"instructor:\s+(.+?)\s+(?:fall|spring|summer|winter)\s+\d{4}",
                text,
                flags=re.I,
            )
            if instr:
                details["instructor"] = instr
            break

    return details


def extract_rows_from_text(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = [clean_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    for index, line in enumerate(lines):
        code = find_course_code(line)
        if not code:
            continue
        if not re.match(rf"^{re.escape(code)}(?:\s+\||\s+|$)", line):
            continue

        block_lines = [line]
        for next_line in lines[index + 1 :]:
            next_code = find_course_code(next_line)
            if next_code and re.match(rf"^{re.escape(next_code)}(?:\s+\||\s+|$)", next_line):
                break
            block_lines.append(next_line)

        if re.match(rf"^{re.escape(code)}\s+\|", line):
            header_start = find_prior_course_header(lines, index, code)
            if header_start >= 0:
                block_lines = lines[header_start:index] + block_lines

        window = " ".join(block_lines)
        if not re.search(r"(class#:\s*\d+|section:\s*[A-Z0-9]+|class status:\s*(open|closed|wait))", window, re.I):
            continue
        rows.append(
            {
                "code": code,
                "crn": find_first(r"class#:\s*(\d{4,6})", window, flags=re.I),
                "section": find_first(r"\b(?:Section|Sec)[:\s]+([A-Z0-9]+)\b", window, flags=re.I),
                "status": (find_first(r"class status:\s*(.+?)(?=\s+\w+:|$)", window, flags=re.I)
                           or find_first(r"\b(Open|Closed|Wait List|Waitlist|Cancelled)\b", window, flags=re.I)),
                "title": extract_title_from_header_line(line, code),
                "source_row": block_lines,
            }
        )
    return rows


def extract_title_from_header_line(line: str, code: str) -> str:
    title = sanitize_albert_text(line.replace(code, "", 1))
    if re.match(r"^\|\s*[\d.-]+\s+units?$", title, re.I):
        return ""
    return title


def find_prior_course_header(lines: list[str], start_index: int, code: str) -> int:
    for index in range(start_index - 1, -1, -1):
        line = lines[index]
        # Another "| units" line means a new lecture group started — stop here.
        if re.match(rf"^{re.escape(code)}\s+\|", line):
            break
        if re.match(rf"^{re.escape(code)}(?:\s+|$)", line):
            # Only treat as a title header if the line has actual title text after the code,
            # not a bare section marker (which would just be "MATH-UA 140" with nothing after).
            remainder = line[len(code):].strip()
            if remainder:
                return index
            break
        other_code = find_course_code(line)
        if other_code and re.match(rf"^{re.escape(other_code)}(?:\s+\||\s+|$)", line):
            break
    return -1


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = (
            clean_text(row.get("code", "")),
            clean_text(row.get("section", "")),
            clean_text(row.get("crn", "")),
        )
        if not any(key):
            key = (json.dumps(row.get("source_row", ""), sort_keys=True), "", "")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def find_course_code(text: str) -> str:
    m = _COURSE_CODE_RE.search(text)
    return clean_text(m.group(0)) if m else ""


def find_first(pattern: str, text: str, *, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    if not match:
        return ""
    return clean_text(match.group(1) if match.groups() else match.group(0))


def normalize_header(value: str) -> str:
    value = clean_text(value).lower()
    value = _HEADER_NORMALIZE_RE.sub(" ", value)
    return clean_text(value)


def clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


if __name__ == "__main__":
    raise SystemExit(main())
