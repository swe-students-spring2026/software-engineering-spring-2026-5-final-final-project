"""
MongoDB Cache API
A FastAPI microservice that exposes the MongoDB cache to other subsystems.
Other services (e.g. ML) call this instead of connecting to MongoDB directly.

Endpoints:
    GET  /health              - ping MongoDB Atlas
    GET  /cache?query=...     - get a cached result
    POST /cache               - save a result to cache
    DELETE /cache             - clear all cached results
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any

from db import get_cached_result, save_cached_result, clear_cache, health_check

app = FastAPI(title="Rove Beetle MongoDB Cache API")


class SaveRequest(BaseModel):
    query: str
    data: dict[str, Any]


@app.get("/health")
def health():
    """
    Health check — pings MongoDB Atlas.
    Returns 200 if reachable, 503 if not.
    """
    if health_check():
        return {"status": "ok", "mongo": "ok"}
    raise HTTPException(status_code=503, detail="MongoDB Atlas is unreachable")


@app.get("/cache")
def get_cache(query: str):
    """
    Look up a cached search result by query string.
    Returns the cached data if found, 404 if not.
    """
    result = get_cached_result(query, "")
    if result is None:
        raise HTTPException(status_code=404, detail="No cached result found for this query")
    return {"query": query, "data": result}


@app.post("/cache")
def save_cache(body: SaveRequest):
    """
    Save a search result to the MongoDB cache.
    """
    save_cached_result(body.query, "", body.data)
    return {"status": "saved", "query": body.query}


@app.delete("/cache")
def delete_cache():
    """
    Clear all cached results. Useful for testing or resetting state.
    """
    clear_cache()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)