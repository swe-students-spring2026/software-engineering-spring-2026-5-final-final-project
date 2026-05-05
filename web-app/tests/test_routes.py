"""tests for web app routes."""

# pylint: disable=redefined-outer-name
import pytest
from bson import ObjectId
from flask import Flask

from app import routes
from app.routes import (
    check_url,
    debug,
    gallery,
    generate_meme_record,
    get_ml_error_detail,
    index,
    is_article_extraction_error,
    make_request_data,
    meme_detail,
    premium_article_message,
    show_error,
    submit,
)


class FakeCursor:
    """Fake MongoDB cursor with sort chaining."""

    def __init__(self, documents):
        self.documents = documents

    def sort(self, _field, _direction):
        """Return the same cursor after sorting."""
        return self

    def __iter__(self):
        """Iterate over fake documents."""
        return iter(self.documents)


class FakeCollection:
    """Fake MongoDB collection for route tests."""

    def __init__(self, documents=None, document=None):
        self.documents = documents or []
        self.document = document
        self.inserted = None

    def find(self):
        """Return fake documents."""
        return FakeCursor(self.documents)

    def find_one(self, _query):
        """Return one fake document."""
        return self.document

    def insert_one(self, document):
        """Capture an inserted document."""
        self.inserted = document


class FakeResponse:
    """Fake requests response."""

    def __init__(self, body, status_code=200):
        self.body = body
        self.status_code = status_code
        self.text = body if isinstance(body, str) else ""

    def raise_for_status(self):
        """Simulate a successful response."""
        if self.status_code >= 400:
            raise routes.requests.HTTPError(response=self)

    def json(self):
        """Return fake JSON."""
        if isinstance(self.body, str):
            raise ValueError("not json")
        return self.body


@pytest.fixture(name="flask_app")
def fixture_flask_app():
    """Create a Flask app for request contexts."""
    app = Flask(__name__)
    app.register_blueprint(routes.main)
    return app


def test_check_url_empty():
    """Check empty URL handling."""
    assert check_url("") is False


def test_check_url_normal():
    """Check non-empty URL handling."""
    assert check_url("https://example.com") is True


def test_make_request_data_empty():
    """Check request data rejects missing URL."""
    with pytest.raises(ValueError):
        make_request_data("")


def test_make_request_data_normal():
    """Check request data shape."""
    assert make_request_data("https://example.com") == {"url": "https://example.com"}


def test_show_error():
    """check error message."""
    assert show_error("bad url") == "error: bad url"


def test_generate_meme_record_posts_to_ml(monkeypatch):
    """Check form data is sent to the ML service."""
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse({"record_id": "record-1"})

    monkeypatch.setattr(routes, "ML_URL", "http://ml:8000")
    monkeypatch.setattr(routes.requests, "post", fake_post)

    assert (
        generate_meme_record("Ada", "https://example.com", "Example text", "drake")[
            "record_id"
        ]
        == "record-1"
    )
    assert captured == {
        "url": "http://ml:8000/generate",
        "json": {
            "person_name": "Ada",
            "source_url": "https://example.com",
            "text": None,
            "template": "drake",
        },
        "timeout": 90,
    }


def test_generate_meme_record_requires_input():
    """Check missing article input is rejected."""
    with pytest.raises(ValueError):
        generate_meme_record("Ada", "", "")


def test_get_ml_error_detail_from_json_response():
    """Check ML error details are extracted from JSON bodies."""
    exc = routes.requests.HTTPError(response=FakeResponse({"detail": "bad article"}))

    assert get_ml_error_detail(exc) == "bad article"


def test_get_ml_error_detail_from_text_json_response():
    """Check ML error details are extracted from JSON text bodies."""
    exc = routes.requests.HTTPError(
        response=FakeResponse('{"detail":"Could not extract article from URL"}')
    )

    assert get_ml_error_detail(exc) == "Could not extract article from URL"


def test_is_article_extraction_error():
    """Check article extraction error detection."""
    assert is_article_extraction_error("Could not extract article from URL")
    assert not is_article_extraction_error("OPENAI_API_KEY is not set")


def test_index_renders_memes(monkeypatch):
    """Check index renders serialized meme ids."""
    object_id = ObjectId()
    fake_collection = FakeCollection([{"_id": object_id, "summary": "x"}])
    monkeypatch.setattr(routes, "collection", fake_collection)
    monkeypatch.setattr(
        routes,
        "render_template",
        lambda template, **context: {"template": template, "context": context},
    )

    response = index()

    assert response == {
        "template": "index.html",
        "context": {
            "memes": [{"_id": str(object_id), "summary": "x"}],
            "templates": routes.SUPPORTED_TEMPLATES,
        },
    }


def test_debug_returns_count(monkeypatch):
    """Check debug route response."""
    monkeypatch.setattr(routes, "collection", FakeCollection([{"summary": "x"}]))

    assert debug()["count"] == 1


def test_meme_detail_not_found(monkeypatch):
    """Check missing meme detail response."""
    monkeypatch.setattr(routes, "collection", FakeCollection())

    assert meme_detail(str(ObjectId())) == ("Not found", 404)


def test_meme_detail_renders_meme(monkeypatch):
    """Check meme detail renders serialized id."""
    object_id = ObjectId()
    monkeypatch.setattr(
        routes,
        "collection",
        FakeCollection(document={"_id": object_id, "summary": "x"}),
    )
    monkeypatch.setattr(
        routes,
        "render_template",
        lambda template, **context: {"template": template, "context": context},
    )

    response = meme_detail(str(object_id))

    assert response == {
        "template": "detail.html",
        "context": {"meme": {"_id": str(object_id), "summary": "x"}},
    }


def test_gallery_renders_memes(monkeypatch):
    """Check gallery route response."""
    monkeypatch.setattr(routes, "collection", FakeCollection([{"summary": "x"}]))
    monkeypatch.setattr(
        routes,
        "render_template",
        lambda template, **context: {"template": template, "context": context},
    )

    assert gallery() == {
        "template": "gallery.html",
        "context": {"memes": [{"summary": "x"}]},
    }


def test_submit_generates_meme(monkeypatch, flask_app):
    """Check submit route triggers meme generation."""
    fake_collection = FakeCollection()
    monkeypatch.setattr(routes, "collection", fake_collection)
    generated = {}
    monkeypatch.setattr(
        routes,
        "generate_meme_record",
        lambda name, url, text, template: generated.update(
            {"name": name, "url": url, "text": text, "template": template}
        ),
    )

    with flask_app.test_request_context(
        "/submit",
        method="POST",
        data={
            "name": "Ada",
            "article-link": "https://example.com",
            "article-text": "Example text",
            "template": "wonka",
        },
    ):
        response = submit()

    assert response.status_code == 302
    assert fake_collection.inserted is None
    assert generated == {
        "name": "Ada",
        "url": "https://example.com",
        "text": "Example text",
        "template": "wonka",
    }


def test_submit_renders_premium_message_for_extraction_error(monkeypatch, flask_app):
    """Check unreadable URL errors are rendered on the form."""

    def fake_generate(_name, _url, _text, _template):
        response = FakeResponse(
            {"detail": "Could not extract article from URL"}, status_code=502
        )
        response.raise_for_status()

    monkeypatch.setattr(routes, "generate_meme_record", fake_generate)
    monkeypatch.setattr(
        routes,
        "render_template",
        lambda template, **context: {"template": template, "context": context},
    )

    with flask_app.test_request_context(
        "/submit",
        method="POST",
        data={
            "name": "Ada",
            "article-link": "https://example.com/paywalled",
            "article-text": "",
            "template": "doge",
        },
    ):
        response = submit()

    assert response == (
        {
            "template": "index.html",
            "context": {
                "error": premium_article_message(),
                "templates": routes.SUPPORTED_TEMPLATES,
            },
        },
        400,
    )