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

def test_report_lateness_page_shows_accepted_users(client, monkeypatch):
    """Test report page shows only users who accepted"""
    user_id = ObjectId()
    event_id = ObjectId()
    
    fake_event = {
        "_id": event_id,
        "host_id": str(user_id),
        "name": "Test Event",
        "invitees_list": [
            {"user_id": "user1", "name": "John", "status": "accepted"},
            {"user_id": "user2", "name": "Jane", "status": "pending"},
        ]
    }
    
    fake_events = FakeEventsCollection(existing_event=fake_event)
    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "events_owned": {str(event_id): datetime.now()},
        }
    )
    
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    monkeypatch.setattr(app_module, "get_db", lambda: FakeDB(fake_events))
    
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
    
    response = client.get(f"/host-events/{event_id}/report")
    
    assert response.status_code == 200
    assert b"John" in response.data
    assert b"Jane" not in response.data


def test_submit_lateness_updates_user(client, monkeypatch):
    # create fake ids
    user_id = ObjectId()
    event_id = ObjectId()
    invitee_id = ObjectId()
    
    # fake event with one accepted user
    fake_event = {
        "_id": event_id,
        "host_id": str(user_id),
        "invitees_list": [{"user_id": str(invitee_id), "name": "John", "status": "accepted"}]
    }
    
    # track updates
    updated = []
    class TrackingUsers(FakeUsersCollection):
        def update_one(self, query, update):
            updated.append(update)
    
    fake_users = TrackingUsers(existing_user={"_id": user_id, "lateness": []})
    fake_events = FakeEventsCollection(existing_event=fake_event)
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    monkeypatch.setattr(app_module, "get_db", lambda: FakeDB(fake_events))
    
    # login the user
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
    
    # submit lateness report
    response = client.post(f"/host-events/{event_id}/report/submit", 
                          data={f"lateness_{invitee_id}": "15"})
    
    # check redirect worked
    assert response.status_code == 302
    
    # make sure that the lateness was added to array
    assert any("$push" in u and u["$push"].get("lateness") == 15 for u in updated)

def test_report_page_loads(client, monkeypatch):
    # make fake user and event
    user_id = ObjectId()
    event_id = ObjectId()
    
    # fake event with accepted user
    fake_event = {
        "_id": event_id,
        "host_id": str(user_id),
        "name": "Test Event",
        "invitees_list": [{"user_id": "123", "name": "John", "status": "accepted"}]
    }
    
    # fake user
    fake_users = FakeUsersCollection(
        existing_user={"_id": user_id, "events_owned": {str(event_id): datetime.now()}}
    )
    fake_events = FakeEventsCollection(existing_event=fake_event)
    
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    monkeypatch.setattr(app_module, "get_db", lambda: FakeDB(fake_events))
    
    # login
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
    
    # test report page loads
    response = client.get(f"/host-events/{event_id}/report")
    assert response.status_code == 200

def test_create_host_event_success(client, monkeypatch):
    user_id = ObjectId()
    
    # mock users
    fake_users = FakeUsersCollection(
        existing_user={
            "_id": user_id,
            "name": "Host",
            "events_owned": {}
        }
    )
    
    # mock event insert
    inserted_events = []
    class FakeEvents:
        def insert_one(self, doc):
            inserted_events.append(doc)
            return type('obj', (object,), {'inserted_id': ObjectId()})()
        def find_one(self, query):
            return None
    
    fake_events = FakeEvents()
    
    def mock_get_db():
        return type('db', (object,), {'__getitem__': lambda self, x: fake_events if x == "events" else None})()
    
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    monkeypatch.setattr(app_module, "get_db", mock_get_db)
    monkeypatch.setattr(app_module, "get_lateness_penalty", lambda x: 0)
    
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
    
    response = client.post("/host-events/create", data={
        "name": "Party",
        "location": "NYC",
        "date": "2026-12-31",
        "time": "20:00",
        "details": "Fun party",
        "invitee_username": ["friend1", "friend2"]
    })
    
    assert response.status_code == 302
    assert len(inserted_events) == 1

def test_delete_host_event(client, monkeypatch):
    # make fake ids
    user_id = ObjectId()
    event_id = ObjectId()
    invitee_id = ObjectId()
    
    # fake event
    fake_event = {
        "_id": event_id,
        "host_id": str(user_id),
        "invitees_list": [{"user_id": str(invitee_id)}]
    }
    
    # custom class with delete_one method
    class FakeEventsWithDelete:
        def __init__(self):
            self.event = fake_event
            self.deleted = False
            self.called = 0
            
        def find_one(self, query):
            self.called += 1
            return self.event
            
        def delete_one(self, query):
            self.deleted = True
    
    # create instance
    fake_events = FakeEventsWithDelete()
    
    # custom db
    class CustomDB:
        def __getitem__(self, name):
            if name == "events":
                return fake_events
            elif name == "users":
                return FakeUsersCollection(existing_user={"_id": user_id})
            raise KeyError(name)
    
    monkeypatch.setattr(app_module, "get_users_collection", lambda: FakeUsersCollection(existing_user={"_id": user_id, "events_owned": {str(event_id): datetime.now()}}))
    monkeypatch.setattr(app_module, "get_db", lambda: CustomDB())
    
    # login
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
    
    # delete
    response = client.get(f"/host-events/{event_id}/delete")
    
    # check
    assert response.status_code == 302
    assert fake_events.deleted == True

def test_edit_host_event_get(client, monkeypatch):
    user_id = ObjectId()
    event_id = ObjectId()
    
    fake_event = {
        "_id": event_id,
        "host_id": str(user_id),
        "name": "Old Name",
        "date": datetime(2026, 12, 31, 20, 0),
        "invitees_list": []
    }
    
    fake_users = FakeUsersCollection(existing_user={"_id": user_id})
    fake_events = FakeEventsCollection(existing_event=fake_event)
    
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    monkeypatch.setattr(app_module, "get_db", lambda: FakeDB(fake_events))
    
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
    
    response = client.get(f"/host-events/{event_id}/edit")
    
    assert response.status_code == 200

def test_accept_event(client, monkeypatch):
    # make fake ids
    user_id = ObjectId()
    event_id = ObjectId()
    
    # fake event
    fake_event = {
        "_id": event_id,
        "invitees_list": [{"user_id": str(user_id), "suggested_arrival_time": datetime.now()}]
    }
    
    # track updates
    updated_users = []
    
    # fake users that tracks updates
    class FakeUsersWithUpdate:
        def __init__(self):
            self.updated = []
            
        def find_one(self, query):
            return {"_id": user_id}
            
        def update_one(self, query, update):
            self.updated.append(update)
    
    fake_users = FakeUsersWithUpdate()
    
    # fake events
    class FakeEventsWithFind:
        def find_one(self, query):
            return fake_event
            
        def update_one(self, query, update):
            pass
    
    fake_events = FakeEventsWithFind()
    
    # fake db with both collections
    class FakeDBWithBoth:
        def __getitem__(self, name):
            if name == "events":
                return fake_events
            elif name == "users":
                return fake_users
            raise KeyError(name)
    
    # mock the database
    monkeypatch.setattr(app_module, "get_db", lambda: FakeDBWithBoth())
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    
    # login
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
    
    # accept the invite
    response = client.get(f"/invites/{event_id}/accept")
    
    # check redirect worked
    assert response.status_code == 302

def test_create_host_event_page_loads(client, monkeypatch):
    # make fake user
    user_id = ObjectId()
    
    fake_users = FakeUsersCollection(existing_user={"_id": user_id})
    
    # mock get_db to return a fake db
    class FakeDB:
        def __getitem__(self, name):
            return None
    
    monkeypatch.setattr(app_module, "get_users_collection", lambda: fake_users)
    monkeypatch.setattr(app_module, "get_db", lambda: FakeDB())
    
    # login
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
    
    # test page loads
    response = client.get("/host-events/create")
    assert response.status_code == 200