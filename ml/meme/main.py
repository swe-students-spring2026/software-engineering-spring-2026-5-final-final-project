from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .captioner import generate_caption
from .db import get_meme_by_id, get_recent_memes, ping_database, save_meme_record
from .memegen_client import DEFAULT_TEMPLATE, SUPPORTED_TEMPLATES, build_response

app = FastAPI(
    title="Meme Generator Service",
    description="Meme generator API that turns article text or summaries into meme captions and stores meme history in MongoDB.",
    version="0.4.0",
)


class GenerateRequest(BaseModel):
    person_name: str = Field(
        ..., min_length=1, description="Name of the person submitting the article"
    )
    text: str | None = Field(
        default=None, description="Article summary or pasted article text"
    )
    source_url: str | None = Field(
        default=None, description="Original article URL if one exists"
    )
    template: str = Field(default=DEFAULT_TEMPLATE, description="Memegen template ID")


class GenerateResponse(BaseModel):
    person_name: str
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
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


def database_status() -> str:
    if not os.getenv("MONGODB_URI"):
        return "not_configured"
    return "connected" if ping_database() else "unreachable"


def build_record(
    payload: GenerateRequest, response: dict[str, str | None], article_text: str
) -> dict[str, object]:
    return {
        "person_name": payload.person_name,
        "source_url": payload.source_url,
        "article_text": article_text,
        "article_summary": response["article_summary"],
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
def history(
    limit: int = Query(default=20, ge=1, le=100)
) -> dict[str, list[dict[str, object]]]:
    items = get_recent_memes(limit=limit)
    return {"items": items}


@app.get("/history/{record_id}", response_model=HistoryItem)
def history_item(record_id: str) -> dict[str, object]:
    item = get_meme_by_id(record_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Meme record not found")
    return item


def get_article_summary(payload: GenerateRequest) -> tuple[str, str]:
    """Return summary text and article text for a generate request."""
    article_text = (payload.text or "").strip()
    if article_text:
        return article_text, article_text

    source_url = (payload.source_url or "").strip()
    if not source_url:
        raise HTTPException(status_code=400, detail="Article text or URL is required")

    try:
        summary = summarize_url(source_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return summary["article_summary"], summary.get("article_text") or source_url


def summarize_url(source_url: str) -> dict[str, str | None]:
    """Summarize a URL using the summary module."""
    from summary.app.summarizer import summarize_article

    return summarize_article(source_url)


@app.post("/generate", response_model=GenerateResponse)
def generate_meme(payload: GenerateRequest) -> dict[str, str | None]:
    article_summary, article_text = get_article_summary(payload)
    caption = generate_caption(article_summary)
    response = build_response(payload.template, caption.top, caption.bottom)
    response["person_name"] = payload.person_name
    response["source_url"] = payload.source_url
    response["article_summary"] = article_summary
    response["record_id"] = save_meme_record(
        build_record(payload, response, article_text)
    )
    return response
