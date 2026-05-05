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
    person_name: str = Field(..., min_length=1, description="Name of the person submitting the article")
    text: str = Field(..., min_length=1, description="Article summary or pasted article text")
    source_url: str | None = Field(default=None, description="Original article URL if one exists")
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

def build_record(payload: GenerateRequest, response: dict[str, str | None]) -> dict[str, object]:
    return {
        "person_name": payload.person_name,
        "source_url": payload.source_url,
        "article_text": payload.text,
        "article_summary": payload.text,
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
    items = get_recent_memes(limit=limit)
    return {"items": items}

@app.get("/history/{record_id}", response_model=HistoryItem)
def history_item(record_id: str) -> dict[str, object]:
    item = get_meme_by_id(record_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Meme record not found")
    return item

@app.post("/generate", response_model=GenerateResponse)
def generate_meme(payload: GenerateRequest) -> dict[str, str | None]:
    caption = generate_caption(payload.text)
    response = build_response(payload.template, caption.top, caption.bottom)
    response["person_name"] = payload.person_name
    response["source_url"] = payload.source_url
    response["article_summary"] = payload.text
    response["record_id"] = save_meme_record(build_record(payload, response))
    return response

