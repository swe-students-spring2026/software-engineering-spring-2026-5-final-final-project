import os
import sys
from datetime import datetime

import pytest
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.app as app_module
from app.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_index_redirects_to_sign_in(client):
    response = client.get("/")

    assert response.status_code == 302
    assert "/sign-in" in response.location


def test_sign_in_page_loads(client):
    response = client.get("/sign-in")

    assert response.status_code == 200


def test_create_account_page_loads(client):
    response = client.get("/create-account")

    assert response.status_code == 200


def test_home_upcoming_requires_login(client):
    response = client.get("/home-upcoming")

    assert response.status_code == 302
    assert "/sign-in" in response.location


def test_home_past_requires_login(client):
    response = client.get("/home-past")

    assert response.status_code == 302
    assert "/sign-in" in response.location


def test_invites_requires_login(client):
    response = client.get("/invites")

    assert response.status_code == 302
    assert "/sign-in" in response.location


def test_host_events_requires_login(client):
    response = client.get("/host-events")

    assert response.status_code == 302
    assert "/sign-in" in response.location


def test_user_dashboard_requires_login(client):
    response = client.get("/user")

    assert response.status_code == 302
    assert "/sign-in" in response.location


def test_create_account_missing_fields_does_not_crash(client):
    response = client.post("/create-account", data={})

    assert response.status_code == 200
    assert b"Please fill in all fields." in response.data


class FakeUsersCollection:
    def __init__(self, existing_user=None):
        self.existing_user = existing_user
        self.inserted_users = []
        self.updated_users = []

    def find_one(self, query):
        return self.existing_user

    def insert_one(self, user):
        self.inserted_users.append(user)

    def update_one(self, query, update):
        self.updated_users.append({"query": query, "update": update})


def test_create_account_success_redirects_to_sign_in(client, monkeypatch):
    fake_users = FakeUsersCollection()
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)

    response = client.post(
        "/create-account",
        data={
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
        },
    )

    assert response.status_code == 302
    assert "/sign-in" in response.location
    assert len(fake_users.inserted_users) == 1
    assert fake_users.inserted_users[0]["name"] == "Test User"
    assert fake_users.inserted_users[0]["phone_number"] == "1234567890"


def test_create_account_duplicate_user_shows_error(client, monkeypatch):
    fake_users = FakeUsersCollection(existing_user={"phone_number": "1234567890"})
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)

    response = client.post(
        "/create-account",
        data={
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
        },
    )

    assert response.status_code == 200
    assert b"User already exists" in response.data
    assert fake_users.inserted_users == []


def test_sign_in_invalid_user_shows_error(client, monkeypatch):
    fake_users = FakeUsersCollection(existing_user=None)
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)

    response = client.post(
        "/sign-in",
        data={
            "phone_number": "1234567890",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 200
    assert b"Invalid phone number or password" in response.data


def test_sign_in_success_redirects_to_home_upcoming(client, monkeypatch):
    fake_users = FakeUsersCollection(
        existing_user={
            "_id": ObjectId(),
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
        }
    )
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)

    response = client.post(
        "/sign-in",
        data={
            "phone_number": "1234567890",
            "password": "testpassword",
        },
    )

    assert response.status_code == 302
    assert "/home-upcoming" in response.location


def test_sign_out_requires_login(client):
    response = client.get("/sign-out")

    assert response.status_code == 302
    assert "/sign-in" in response.location


def test_format_time_morning_time():
    date = datetime(2026, 5, 1, 9, 5)

    result = app_module.format_time(date)

    assert result == "9:05 AM, May 1st, 2026"


def test_format_time_afternoon_time():
    date = datetime(2026, 5, 2, 15, 30)

    result = app_module.format_time(date)

    assert result == "3:30 PM, May 2nd, 2026"


def test_format_time_uses_th_for_teen_dates():
    date = datetime(2026, 5, 11, 0, 0)

    result = app_module.format_time(date)

    assert result == "12:00 AM, May 11th, 2026"


def test_user_dashboard_empty_update_shows_error(client, monkeypatch):
    user_id = ObjectId()
    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
        }
    )
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    response = client.post("/user", data={})

    assert response.status_code == 200
    assert b"No changes to save" in response.data
    assert fake_users.updated_users == []


def test_user_dashboard_updates_user(client, monkeypatch):
    user_id = ObjectId()
    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
        }
    )
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    response = client.post(
        "/user",
        data={
            "name": "Updated User",
            "phone_number": "9876543210",
            "password": "newpassword",
        },
    )

    assert response.status_code == 200
    assert b"Saved" in response.data
    assert len(fake_users.updated_users) == 1
    assert fake_users.updated_users[0]["update"]["$set"]["name"] == "Updated User"
    assert fake_users.updated_users[0]["update"]["$set"]["phone_number"] == "9876543210"
    assert fake_users.updated_users[0]["update"]["$set"]["password"] == "newpassword"


def test_sign_in_redirects_if_already_logged_in(client, monkeypatch):
    user_id = ObjectId()
    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
        }
    )
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    response = client.get("/sign-in")

    assert response.status_code == 302
    assert "/home-upcoming" in response.location


def test_create_account_redirects_if_already_logged_in(client, monkeypatch):
    user_id = ObjectId()
    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
        }
    )
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    response = client.get("/create-account")

    assert response.status_code == 302
    assert "/home-upcoming" in response.location


def test_index_redirects_to_home_if_logged_in(client, monkeypatch):
    user_id = ObjectId()
    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
        }
    )
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    response = client.get("/")

    assert response.status_code == 302
    assert "/home-upcoming" in response.location


class FakeEventsCollection:
    def __init__(self, existing_event=None):
        self.existing_event = existing_event

    def find_one(self, query):
        return self.existing_event


class FakeDB:
    def __init__(self, events_collection):
        self.events_collection = events_collection

    def __getitem__(self, collection_name):
        if collection_name == "events":
            return self.events_collection
        raise KeyError(collection_name)


def test_home_upcoming_shows_upcoming_owned_event(client, monkeypatch):
    user_id = ObjectId()
    event_id = ObjectId()
    event_datetime = datetime(2026, 6, 1, 18, 30)

    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
            "events_owned": {str(event_id): event_datetime},
            "events_accepted": {},
        }
    )
    fake_events = FakeEventsCollection(
        existing_event={
            "_id": event_id,
            "name": "Dinner Party",
            "location": "NYC",
            "description": "Bring snacks",
        }
    )

    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    monkeypatch.setattr(app_module, "get_db", lambda: FakeDB(fake_events))

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    response = client.get("/home-upcoming")

    assert response.status_code == 200
    assert b"Dinner Party" in response.data
    assert b"NYC" in response.data


def test_home_past_shows_past_accepted_event(client, monkeypatch):
    user_id = ObjectId()
    event_id = ObjectId()
    event_datetime = datetime(2020, 6, 1, 18, 30)

    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
            "events_owned": {},
            "events_accepted": {str(event_id): event_datetime},
        }
    )
    fake_events = FakeEventsCollection(
        existing_event={
            "_id": event_id,
            "name": "Old Dinner",
            "location": "Brooklyn",
            "description": "Past event",
        }
    )

    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    monkeypatch.setattr(app_module, "get_db", lambda: FakeDB(fake_events))

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    response = client.get("/home-past")

    assert response.status_code == 200
    assert b"Old Dinner" in response.data
    assert b"Brooklyn" in response.data


def test_invites_shows_invited_event(client, monkeypatch):
    user_id = ObjectId()
    event_id = ObjectId()
    event_datetime = datetime(2026, 6, 1, 18, 30)

    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "name": "Test User",
            "phone_number": "1234567890",
            "password": "testpassword",
            "event_invites": {str(event_id): event_datetime},
        }
    )
    fake_events = FakeEventsCollection(
        existing_event={
            "_id": event_id,
            "name": "Birthday Invite",
            "location": "Queens",
            "description": "Please come",
        }
    )

    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    monkeypatch.setattr(app_module, "get_db", lambda: FakeDB(fake_events))

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    response = client.get("/invites")

    assert response.status_code == 200
    assert b"Birthday Invite" in response.data
    assert b"Queens" in response.data