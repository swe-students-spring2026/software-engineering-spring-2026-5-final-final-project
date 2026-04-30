"""
Placeholder service layer. Replace each function body with real API calls
when the backend and ML subsystem are ready.
"""

PLACEHOLDER_MOVIES = [
    {
        "id": "1",
        "title": "Lorem Ipsum: The Movie",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque euismod.",
        "genre": "Drama",
        "year": 2023,
        "rating": 7.4,
        "poster_url": "https://placehold.co/300x450/1a1a2e/a78bfa?text=Lorem+Ipsum",
    },
    {
        "id": "2",
        "title": "Dolor Sit Amet",
        "description": "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "genre": "Thriller",
        "year": 2022,
        "rating": 8.1,
        "poster_url": "https://placehold.co/300x450/1a1a2e/a78bfa?text=Dolor+Sit+Amet",
    },
    {
        "id": "3",
        "title": "Consectetur Rising",
        "description": "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
        "genre": "Action",
        "year": 2024,
        "rating": 6.9,
        "poster_url": "https://placehold.co/300x450/1a1a2e/a78bfa?text=Consectetur+Rising",
    },
]

PLACEHOLDER_FAVORITES = [
    {
        "id": "1",
        "title": "Lorem Ipsum: The Movie",
        "year": 2023,
        "poster_url": "https://placehold.co/300x450/1a1a2e/a78bfa?text=Lorem+Ipsum",
    },
    {
        "id": "2",
        "title": "Dolor Sit Amet",
        "year": 2022,
        "poster_url": "https://placehold.co/300x450/1a1a2e/a78bfa?text=Dolor+Sit+Amet",
    },
    {
        "id": "3",
        "title": "Consectetur Rising",
        "year": 2024,
        "poster_url": "https://placehold.co/300x450/1a1a2e/a78bfa?text=Consectetur+Rising",
    },
    {
        "id": "4",
        "title": "Adipiscing Elite",
        "year": 2021,
        "poster_url": "https://placehold.co/300x450/1a1a2e/a78bfa?text=Adipiscing+Elite",
    },
]


def search_movies(query: str) -> list[dict]:
    """Standard keyword search — returns matching movies from the database/API."""
    # TODO: replace with real backend API call
    return PLACEHOLDER_MOVIES


def recommend_movies(movie_ids: list[str]) -> list[dict]:
    """Return recommendations based on a list of favourite movie IDs."""
    # TODO: replace with real ML subsystem call (POST /recommend)
    return PLACEHOLDER_MOVIES


def get_movie_details(movie_id: str) -> dict:
    """Fetch full details for a single movie by ID."""
    # TODO: replace with real backend API call
    return {
        "id": movie_id,
        "title": "Lorem Ipsum: The Movie",
        "description": (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Pellentesque euismod magna vel nisi scelerisque, at tincidunt "
            "erat laoreet. Nullam ac tortor vitae purus faucibus blandit."
        ),
        "genre": "Drama",
        "year": 2023,
        "rating": 7.4,
        "director": "Jane Doe",
        "cast": ["Actor One", "Actor Two", "Actor Three"],
    }


def get_favorites() -> list[dict]:
    """Fetch the current user's saved favorites."""
    # TODO: replace with real backend API call (pass user session/token)
    return PLACEHOLDER_FAVORITES
