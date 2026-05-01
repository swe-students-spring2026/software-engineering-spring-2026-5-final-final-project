"""Minimal web-app tests
"""

from __future__ import annotations

import os
import sys
import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import pytest
from bson.objectid import ObjectId


def _import_web_app_module():
    os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
    os.environ.setdefault("MONGO_DBNAME", "potatoes_test")
    os.environ.setdefault("SECRET_KEY", "test")

    try:
        import app as web_app_module  # type: ignore
    except ModuleNotFoundError:
        web_app_dir = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(web_app_dir))
        import app as web_app_module  # type: ignore

    return web_app_module


@pytest.fixture()
def web_app_module():
    return _import_web_app_module()


@pytest.fixture()
def flask_app(web_app_module):
    return web_app_module.app


def test_login_page_renders(flask_app):
    client = flask_app.test_client()
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"<h1>Login</h1>" in resp.data


def test_signup_page_renders(flask_app):
    client = flask_app.test_client()
    resp = client.get("/signup")
    assert resp.status_code == 200
    assert b"Sign Up" in resp.data or b"Create Account" in resp.data


def test_protected_home_redirects_to_login(flask_app):
    client = flask_app.test_client()
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302)
    assert "/login" in (resp.headers.get("Location") or "")


def test_login_success_redirects_to_home(monkeypatch, flask_app, web_app_module):
    class FakeUsers:
        def find_one(self, query):
            if query == {"email": "test@example.com"}:
                return {"_id": "u1", "email": "test@example.com", "password": "pw"}
            return None

    monkeypatch.setattr(web_app_module, "db", SimpleNamespace(users=FakeUsers()))

    client = flask_app.test_client()
    resp = client.post(
        "/login",
        data={"email": "test@example.com", "password": "pw"},
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302)
    assert resp.headers.get("Location", "").endswith("/")


def test_login_invalid_credentials_shows_error(monkeypatch, flask_app, web_app_module):
    class FakeUsers:
        def find_one(self, _query):
            return None

    monkeypatch.setattr(web_app_module, "db", SimpleNamespace(users=FakeUsers()))

    client = flask_app.test_client()
    resp = client.post("/login", data={"email": "nope@example.com", "password": "bad"})
    assert resp.status_code == 200
    assert b"Invalid email or password" in resp.data


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)
    def sort(self, field, direction):
        self.docs.sort(key=lambda doc: doc.get(field) or dt.datetime.min, reverse=direction < 0)
        return self
    def limit(self, count): self.docs = self.docs[:count]; return self
    def __iter__(self): return iter(self.docs)
class FakeCollection:
    def __init__(self, docs=()):
        self.docs = [dict(doc) for doc in docs]
    def find_one(self, query, projection=None):
        return next((self._project(doc, projection) for doc in self.docs if self._matches(doc, query)), None)
    def find(self, query=None, projection=None):
        return FakeCursor(
            self._project(doc, projection)
            for doc in self.docs
            if self._matches(doc, query or {})
        )
    def insert_one(self, doc):
        new_doc = dict(doc, _id=doc.get("_id", ObjectId()))
        self.docs.append(new_doc)
        return SimpleNamespace(inserted_id=new_doc["_id"])
    def update_one(self, query, update):
        doc = self.find_one(query)
        if doc:
            real_doc = self.find_one({"_id": doc["_id"]})
            real_doc.update(update.get("$set", {}))
        return SimpleNamespace(matched_count=1 if doc else 0)
    def delete_one(self, query):
        self.docs = [doc for doc in self.docs if not self._matches(doc, query)]
        return SimpleNamespace()
    def count_documents(self, query):
        return sum(1 for doc in self.docs if self._matches(doc, query))
    def distinct(self, field, query):
        return list(dict.fromkeys(doc.get(field) for doc in self.docs if self._matches(doc, query)))
    def _matches(self, doc, query):
        for key, expected in query.items():
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$regex" in expected and not expected["$regex"].search(str(actual or "")):
                    return False
                if "$exists" in expected and (key in doc) != expected["$exists"]:
                    return False
            elif actual != expected:
                return False
        return True
    def _project(self, doc, projection):
        if projection is None:
            return doc
        picked = {key: doc[key] for key, keep in projection.items() if keep and key in doc}
        if projection.get("_id", 1) and "_id" in doc: picked["_id"] = doc["_id"]
        return picked
@pytest.fixture()
def seeded_app(monkeypatch, web_app_module):
    user_id, prof_id, other_prof_id = ObjectId(), ObjectId(), ObjectId()
    post_id, other_post_id = ObjectId(), ObjectId()
    now = dt.datetime(2026, 1, 1, 12, 0)
    users = FakeCollection([{"_id": user_id, "email": "me@test.com", "password": "pw"}])
    professors = FakeCollection(
        [
            {"_id": prof_id, "name": "Ada Lovelace", "title": "CS", "email": "ada@nyu.edu"},
            {"_id": other_prof_id, "name": "Grace Hopper", "title": "Math", "email": ""},
        ]
    )
    posts = FakeCollection(
        [
            {
                "_id": post_id,
                "professor_id": prof_id,
                "professor_name": "Ada Lovelace",
                "author_email": "me@test.com",
                "text": "Great lectures.",
                "created_at": now,
                "updated_at": now,
                "sentiment": {"overall": {"score": 90, "label": "Very Positive"}, "themes": []},
            },
            {
                "_id": other_post_id,
                "professor_id": prof_id,
                "professor_name": "Ada Lovelace",
                "author_email": "other@test.com",
                "text": "Useful homework.",
                "created_at": now - dt.timedelta(days=1),
                "updated_at": now,
                "sentiment": {"overall": {"score": 70, "label": "Positive"}, "themes": []},
            },
        ]
    )
    fake_db = SimpleNamespace(users=users, professors=professors, posts=posts, groups=FakeCollection())
    monkeypatch.setattr(web_app_module, "db", fake_db)
    monkeypatch.setattr(web_app_module, "users", users)
    monkeypatch.setattr(web_app_module, "professors", professors)
    monkeypatch.setattr(web_app_module, "posts", posts)
    web_app_module.app.config.update(TESTING=True)
    return SimpleNamespace(module=web_app_module, app=web_app_module.app, users=users,
        professors=professors, posts=posts, user_id=user_id, prof_id=prof_id,
        other_prof_id=other_prof_id, post_id=post_id, other_post_id=other_post_id)
@pytest.fixture()
def logged_in_client(seeded_app):
    client = seeded_app.app.test_client()
    resp = client.post("/login", data={"email": "me@test.com", "password": "pw"})
    assert resp.status_code == 302
    return client
def test_signup_logout_and_load_user_paths(seeded_app, logged_in_client):
    client = seeded_app.app.test_client()
    assert b"Email already taken" in client.post(
        "/signup", data={"email": "me@test.com", "password": "pw"}
    ).data
    resp = client.post("/signup", data={"email": "new@test.com", "password": "pw"})
    assert resp.status_code == 302
    assert seeded_app.users.find_one({"email": "new@test.com"})

    assert seeded_app.module.load_user(str(seeded_app.user_id)).email == "me@test.com"
    assert seeded_app.module.load_user("bad-id") is None
    assert logged_in_client.get("/logout").status_code == 302
def test_home_search_and_professor_pages(seeded_app, logged_in_client):
    home = logged_in_client.get("/")
    assert home.status_code == 200
    assert b"Great lectures." in home.data
    assert seeded_app.users.find_one({"_id": seeded_app.user_id})["professors_rated"] == 1

    assert logged_in_client.get("/api/professors/search?q=").json == {"results": []}
    results = logged_in_client.get("/api/professors/search?q=ada").json["results"]
    assert results[0]["name"] == "Ada Lovelace"

    page = logged_in_client.get(f"/professors/{seeded_app.prof_id}")
    assert page.status_code == 200
    assert b"Great lectures." in page.data and b"Useful homework." in page.data
    assert logged_in_client.get("/professors/not-an-id").status_code == 302

    form = logged_in_client.get(f"/professors/{seeded_app.prof_id}/posts/new")
    assert form.status_code == 200
    assert b"Create Post" in form.data
    assert logged_in_client.get("/professors/bad/posts/new").status_code == 302
def test_create_view_edit_and_delete_post(monkeypatch, seeded_app, logged_in_client):
    sentiment = {
        "overall": {"score": 80, "label": "Positive"},
        "themes": [{"theme": "clarity", "score": 80, "label": "Positive"}],
    }
    monkeypatch.setattr(seeded_app.module, "_get_sentiment", lambda _text: sentiment)

    blank = logged_in_client.post(f"/professors/{seeded_app.prof_id}/posts/new", data={"text": " "})
    assert blank.status_code == 302
    created = logged_in_client.post(
        f"/professors/{seeded_app.other_prof_id}/posts/new",
        data={"text": "Clear and organized."},
    )
    assert created.status_code == 302
    new_post = seeded_app.posts.find_one({"professor_id": seeded_app.other_prof_id})
    assert new_post["sentiment"] == sentiment
    assert seeded_app.professors.find_one({"_id": seeded_app.other_prof_id})["sentiment_post_count"] == 1

    assert b"Edit" in logged_in_client.get(f"/posts/{seeded_app.post_id}").data
    assert b"Useful homework." in logged_in_client.get(f"/posts/{seeded_app.other_post_id}").data
    assert logged_in_client.get("/posts/bad-id").status_code == 302

    edit_form = logged_in_client.get(f"/posts/{seeded_app.post_id}/edit")
    assert edit_form.status_code == 200
    assert b"Great lectures." in edit_form.data
    assert logged_in_client.get(f"/posts/{seeded_app.other_post_id}/edit").status_code == 302
    assert logged_in_client.post(f"/posts/{seeded_app.post_id}/edit", data={"text": ""}).status_code == 302
    updated = logged_in_client.post(
        f"/posts/{seeded_app.post_id}/edit?next=home",
        data={"text": "Updated review."},
    )
    assert updated.status_code == 302
    assert seeded_app.posts.find_one({"_id": seeded_app.post_id})["text"] == "Updated review."

    assert logged_in_client.post("/posts/bad/delete").status_code == 302
    assert logged_in_client.post(f"/posts/{seeded_app.other_post_id}/delete").status_code == 302
    deleted = logged_in_client.post(f"/posts/{seeded_app.post_id}/delete?next=home")
    assert deleted.status_code == 302
    assert seeded_app.posts.find_one({"_id": seeded_app.post_id}) is None
def test_helpers_sentiment_client_and_aggregation(monkeypatch, seeded_app):
    module = seeded_app.module
    assert module._normalize_query("  Ada   Lovelace ") == "ada lovelace"
    assert module._name_score("ada", "Ada Lovelace") > module._name_score("zzz", "Ada Lovelace")
    assert [module._polarity_to_label(x) for x in [0.5, 0.2, 0, -0.2, -0.5]] == [
        "Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]

    class GoodResponse:
        def raise_for_status(self): return None
        def json(self): return {"ok": True}

    monkeypatch.setattr(module.http_requests, "post", lambda *args, **kwargs: GoodResponse())
    assert module._get_sentiment("nice") == {"ok": True}
    monkeypatch.setattr(module.http_requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(Exception()))
    assert module._get_sentiment("nice") is None

    empty_prof = ObjectId()
    seeded_app.professors.insert_one({"_id": empty_prof, "name": "No Posts"})
    module._update_professor_sentiment(empty_prof)
    assert "sentiment_overall" not in seeded_app.professors.find_one({"_id": empty_prof})
