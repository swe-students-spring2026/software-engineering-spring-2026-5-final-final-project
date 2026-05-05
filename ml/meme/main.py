from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .captioner import generate_caption
from .db import get_meme_by_id, get_recent_memes, ping_database, save_meme_record
from .memegen_client import DEFAULT_TEMPLATE, SUPPORTED_TEMPLATES, build_response

app = FastAPI(
    title="Meme Generator Service",
    description=(
        "Meme generator API that turns article URLs, summaries, or pasted text "
        "into meme captions and stores meme history in MongoDB."
    ),
    version="0.7.0",
)


class GenerateRequest(BaseModel):
    person_name: str | None = Field(
        default=None,
        description="Name of the person submitting the article or summary",
    )
    summary: str | None = Field(
        default=None,
        description="Summary text from the summarization service",
    )
    text: str | None = Field(
        default=None,
        description="Pasted article text or legacy summary field from the web app",
    )
    title: str | None = Field(
        default=None,
        description="Article title from the summarization service",
    )
    article_type: str | None = Field(
        default=None,
        description="Optional article category from the summarization service",
    )
    source_url: str | None = Field(
        default=None,
        description="Original article URL if one exists",
    )
    template: str | None = Field(
        default=DEFAULT_TEMPLATE,
        description="Memegen template ID",
    )


class GenerateResponse(BaseModel):
    person_name: str | None = None
    template: str
    top_text: str
    bottom_text: str
    meme_url: str
    source_url: str | None = None
    article_summary: str | None = None
    record_id: str | None = None


class HistoryItem(BaseModel):
    id: str
    person_name: str | None = None
    template: str
    top_text: str
    bottom_text: str
    meme_url: str
    source_url: str | None = None
    article_text: str | None = None
    article_summary: str | None = None
    title: str | None = None
    article_type: str | None = None
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


def database_status() -> str:
    if not os.getenv("MONGODB_URI"):
        return "not_configured"
    return "connected" if ping_database() else "unreachable"


def clean_optional_text(value: str | None) -> str | None:
    if value and value.strip():
        return value.strip()
    return None


def resolve_template(template: str | None) -> str:
    normalized = clean_optional_text(template)
    if normalized in SUPPORTED_TEMPLATES:
        return normalized
    return DEFAULT_TEMPLATE


def load_article_summarizer() -> Callable[[str], dict[str, Any]]:
    try:
        from ml.summary.app.summarizer import summarize_article
    except ImportError:
        try:
            from summary.app.summarizer import summarize_article
        except ImportError:
            try:
                from summary.main import summarize_article  # type: ignore
            except ImportError as exc:
                raise RuntimeError("Article summarizer is not available in this build") from exc
    return summarize_article


def summarize_with_openai(article_text: str) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI client is not installed in this build") from exc

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    system_prompt = """You are a news summarization system.
Return JSON only with these keys:
- title: extract or infer the article title
- summary: a neutral, objective summary in 2-3 sentences
- article_type: one of technology, sports, education, product reviews, news, other
Rules:
- Do not add information that is not in the article text.
- Preserve key facts, names, and numbers.
- Use \"other\" if the article does not clearly fit another category."""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Article:\n{article_text[:20000]}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("OpenAI returned an empty response")
    return json.loads(content)


def summarize_pasted_text(
    article_text: str,
) -> tuple[str, str | None, str | None, str | None]:
    try:
        summarize_article = load_article_summarizer()
    except RuntimeError:
        summary_result = summarize_with_openai(article_text)
    else:
        try:
            summary_result = summarize_article(article_text)
        except Exception as exc:
            raise RuntimeError(f"Article summarization failed: {exc}") from exc

    article_summary = clean_optional_text(
        summary_result.get("article_summary") or summary_result.get("summary")
    )
    if article_summary is None:
        raise RuntimeError("Summarizer returned no article summary")

    resolved_text = clean_optional_text(summary_result.get("article_text")) or article_text
    title = clean_optional_text(summary_result.get("title"))
    article_type = clean_optional_text(summary_result.get("article_type"))
    return article_summary, resolved_text, title, article_type


def summarize_url(source_url: str) -> dict[str, Any]:
    summarize_article = load_article_summarizer()
    return summarize_article(source_url)


def summarize_from_url(
    source_url: str,
    payload: GenerateRequest,
) -> tuple[str, str | None, str | None, str | None]:
    try:
        summary_result = summarize_url(source_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    article_summary = clean_optional_text(
        summary_result.get("article_summary") or summary_result.get("summary")
    )
    if article_summary is None:
        raise HTTPException(
            status_code=502,
            detail="Summarizer returned no article summary",
        )

    article_text = clean_optional_text(summary_result.get("article_text"))
    title = clean_optional_text(payload.title) or clean_optional_text(
        summary_result.get("title")
    )
    article_type = clean_optional_text(payload.article_type) or clean_optional_text(
        summary_result.get("article_type")
    )
    return article_summary, article_text, title, article_type


def resolve_article_content(
    payload: GenerateRequest,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    source_url = clean_optional_text(payload.source_url)
    if source_url is not None:
        article_summary, article_text, title, article_type = summarize_from_url(
            source_url, payload
        )
        return article_summary, article_text, title, article_type, source_url

    summary_text = clean_optional_text(payload.summary)
    if summary_text is not None:
        return (
            summary_text,
            None,
            clean_optional_text(payload.title),
            clean_optional_text(payload.article_type),
            None,
        )

    article_text = clean_optional_text(payload.text)
    if article_text is not None:
        try:
            article_summary, article_text, inferred_title, inferred_article_type = summarize_pasted_text(
                article_text
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return (
            article_summary,
            article_text,
            clean_optional_text(payload.title) or inferred_title,
            clean_optional_text(payload.article_type) or inferred_article_type,
            None,
        )

    raise HTTPException(
        status_code=400,
        detail="A source_url, summary, or text value is required",
    )


def build_record(
    person_name: str | None,
    source_url: str | None,
    article_text: str | None,
    article_summary: str,
    title: str | None,
    article_type: str | None,
    response: dict[str, str | None],
) -> dict[str, object]:
    return {
        "person_name": person_name,
        "source_url": source_url,
        "article_text": article_text,
        "article_summary": article_summary,
        "title": title,
        "article_type": article_type,
        "template": response["template"],
        "top_text": response["top_text"],
        "bottom_text": response["bottom_text"],
        "meme_url": response["meme_url"],
        "created_at": datetime.now(timezone.utc),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "database": database_status(),
    }


@app.get("/templates")
def templates() -> dict[str, list[str]]:
    return {"templates": SUPPORTED_TEMPLATES}


@app.get("/history", response_model=HistoryResponse)
def history(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, list[dict[str, object]]]:
    try:
        items = get_recent_memes(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"items": items}


@app.get("/history/{record_id}", response_model=HistoryItem)
def history_item(record_id: str) -> dict[str, object]:
    try:
        item = get_meme_by_id(record_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if item is None:
        raise HTTPException(status_code=404, detail="Meme record not found")

    return item


@app.post("/generate", response_model=GenerateResponse)
def generate_meme(payload: GenerateRequest) -> dict[str, str | None]:
    article_summary, article_text, title, article_type, source_url = (
        resolve_article_content(payload)
    )
    template_id = resolve_template(payload.template)
    person_name = clean_optional_text(payload.person_name)

    caption = generate_caption(article_summary)
    response = build_response(template_id, caption.top, caption.bottom)
    response["person_name"] = person_name
    response["source_url"] = source_url
    response["article_summary"] = article_summary
    response["record_id"] = save_meme_record(
        build_record(
            person_name,
            source_url,
            article_text,
            article_summary,
            title,
            article_type,
            response,
        )
    )
    return response