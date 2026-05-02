"""
Placeholder service layer.

Replace these functions with real backend, MongoDB, and recommendation-engine
API calls when those services are ready. The frontend routes call this layer so
the templates can be built and tested without backend dependencies.
"""

PLACEHOLDER_MOVIES = [
    {
        "id": "1",
        "title": "Lorem Ipsum: The Movie",
        "description": "A character drama about starting over after a public failure.",
        "genre": "Drama",
        "year": 2023,
        "rating": 7.4,
        "similarity": 0.93,
    },
    {
        "id": "2",
        "title": "Dolor Sit Amet",
        "description": "A tense thriller built around a missing witness and one impossible alibi.",
        "genre": "Thriller",
        "year": 2022,
        "rating": 8.1,
        "similarity": 0.89,
    },
    {
        "id": "3",
        "title": "Consectetur Rising",
        "description": "A fast action story about a courier caught between rival syndicates.",
        "genre": "Action",
        "year": 2024,
        "rating": 6.9,
        "similarity": 0.84,
    },
    {
        "id": "4",
        "title": "Nocturne Signal",
        "description": "A quiet sci-fi mystery about memory, distance, and impossible messages.",
        "genre": "Sci-Fi",
        "year": 2021,
        "rating": 7.8,
        "similarity": 0.81,
    },
]


def search_movies(query: str) -> list[dict]:
    """Standard keyword search that returns matching movies from the API."""
    # TODO: replace with real backend API call
    normalized_query = query.lower()
    matches = [
        movie
        for movie in PLACEHOLDER_MOVIES
        if normalized_query in movie["title"].lower()
        or normalized_query in movie["genre"].lower()
    ]
    return matches or PLACEHOLDER_MOVIES


def recommend_movies(query: str) -> list[dict]:
    """Natural-language recommendation search."""
    # TODO: replace with real ML subsystem call
    return [
        {
            **movie,
            "reason": f'Matched your request: "{query}"',
        }
        for movie in PLACEHOLDER_MOVIES
    ]


def recommend_from_favorites(favorite_titles: list[str]) -> list[dict]:
    """Return personalized recommendations based on four favorite movie titles."""
    # TODO: replace with recommendation-engine cosine similarity API call
    favorites = ", ".join(title for title in favorite_titles if title)
    return [
        {
            **movie,
            "reason": f"Cosine similarity match based on: {favorites}",
        }
        for movie in PLACEHOLDER_MOVIES
    ]


def get_movie_details(movie_id: str) -> dict:
    """Fetch full details for a single movie by ID."""
    # TODO: replace with real backend API call
    movie = next(
        (candidate for candidate in PLACEHOLDER_MOVIES if candidate["id"] == movie_id),
        PLACEHOLDER_MOVIES[0],
    )
    return {
        **movie,
        "director": "Jane Doe",
        "cast": ["Actor One", "Actor Two", "Actor Three"],
    }


def get_similar_movies(movie_id: str) -> list[dict]:
    """Fetch movies similar to a selected movie."""
    # TODO: replace with real backend API call using movie_id
    return [movie for movie in PLACEHOLDER_MOVIES if movie["id"] != movie_id][:3]


def get_movies_by_ids(movie_ids: list[str]) -> list[dict]:
    """Fetch movies matching the provided IDs while preserving the ID order."""
    movies_by_id = {movie["id"]: movie for movie in PLACEHOLDER_MOVIES}
    return [movies_by_id[movie_id] for movie_id in movie_ids if movie_id in movies_by_id]


def get_favorites() -> list[dict]:
    """Fetch the current user's saved favorites."""
    # TODO: replace with real backend API call
    return PLACEHOLDER_MOVIES[:2]
