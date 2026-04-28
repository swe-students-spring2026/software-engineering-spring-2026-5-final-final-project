"""
Search routing layer.

Decides whether an incoming query is a direct keyword search or a natural-language
intent query, then dispatches to the appropriate service function.

Routing logic is intentionally simple for now — replace the _is_intent_query
heuristic with a real classifier (ML model, regex, LLM call, etc.) when ready.
"""

from services import api_client

# Queries longer than this word count, or containing multiple spaces,
# are treated as natural-language intent rather than a direct keyword search.
INTENT_WORD_THRESHOLD = 4


def handle_search(query: str) -> dict:
    """
    Entry point for all search requests.

    Returns a dict with:
      - "mode":    "direct" | "intent"
      - "query":   the original query string
      - "results": list of movie dicts
    """
    query = query.strip()

    if _is_intent_query(query):
        results = api_client.recommend_movies(query)
        mode = "intent"
    else:
        results = api_client.search_movies(query)
        mode = "direct"

    return {"mode": mode, "query": query, "results": results}


def _is_intent_query(query: str) -> bool:
    """
    Placeholder heuristic: treat the query as natural-language intent when it
    looks like a sentence rather than a title/keyword.

    TODO: replace with a real classifier or LLM-based detection.
    """
    words = query.split()
    return len(words) > INTENT_WORD_THRESHOLD
