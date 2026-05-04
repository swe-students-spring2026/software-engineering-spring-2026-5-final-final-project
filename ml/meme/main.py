from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl

from app.article_fetcher import ArticleContent, fetch_article_content
from app.captioner import generate_caption
from app.db import get_meme_by_id, get_recent_memes, save_meme_record
from app.memegen_client import DEFAULT_TEMPLATE, SUPPORTED_TEMPLATES, build_response

app = FastAPI(
    title="Meme Generator Service",
    description="Backend service that turns article text, summaries, or article URLs into meme-ready captions.",
    version="0.3.0",
)

class GenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Article text, summary, or any prompt")
    template: str = Field(default=DEFAULT_TEMPLATE, description="Memegen template ID")
    use_ai: bool = Field(default=False, description="Whether to use AI captioning when available")

class GenerateFromUrlRequest(BaseModel):
    url: HttpUrl
    template: str = Field(default=DEFAULT_TEMPLATE, description="Memegen template ID")
    use_ai: bool = Field(default=False, description="Whether to use AI captioning when available")

class GenerateResponse(BaseModel):
    template: str
    top_text: str
    bottom_text: str
    meme_url: str
    source_url: str | None = None
    article_title: str | None = None
    article_summary: str | None = None
    record_id: str | None = None

class HistoryItem(BaseModel):
    id: str
    template: str
    top_text: str
    bottom_text: str
    meme_url: str
    source_url: str | None = None
    article_title: str | None = None
    article_summary: str | None = None
    created_at: datetime

class HistoryResponse(BaseModel):
    items: list[HistoryItem]

def build_record(response: dict[str, str | None]) -> dict[str, str | datetime | None]:
    return {
        "template": response["template"],
        "top_text": response["top_text"],
        "bottom_text": response["bottom_text"],
        "meme_url": response["meme_url"],
        "source_url": response.get("source_url"),
        "article_title": response.get("article_title"),
        "article_summary": response.get("article_summary"),
        "created_at": datetime.now(timezone.utc),
    }

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

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
    caption = generate_caption(payload.text, use_ai=payload.use_ai)
    response = build_response(payload.template, caption.top, caption.bottom)
    response["article_summary"] = payload.text
    response["record_id"] = save_meme_record(build_record(response))
    return response

@app.post("/generate-from-url", response_model=GenerateResponse)
def generate_meme_from_url(payload: GenerateFromUrlRequest) -> dict[str, str | None]:
    try:
        article: ArticleContent = fetch_article_content(str(payload.url))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    text_for_caption = article.summary or article.title
    caption = generate_caption(text_for_caption, use_ai=payload.use_ai)
    response = build_response(payload.template, caption.top, caption.bottom)
    response["source_url"] = str(payload.url)
    response["article_title"] = article.title
    response["article_summary"] = article.summary
    response["record_id"] = save_meme_record(build_record(response))
    return response   