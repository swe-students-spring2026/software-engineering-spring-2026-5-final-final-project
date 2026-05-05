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
    query = query.strip()
    mode = "intent" if _is_intent_query(query) else "direct"
    results = api_client.search_movies(query, mode=mode)
    return {"mode": mode, "query": query, "results": results}


def _is_intent_query(query: str) -> bool:
    words = query.split()
    if len(words) > INTENT_WORD_THRESHOLD:
        return True
    # Single keywords that are clearly descriptive, not titles
    intent_signals = ["thriller", "romantic",
                      "funny", "scary", "action", "drama"]
    lower = query.lower()
    return any(signal in lower for signal in intent_signals)