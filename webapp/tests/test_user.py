from models.user import create_user
from werkzeug.security import check_password_hash


def test_create_user_has_required_fields():
    data = {
        "email": "test@example.com",
        "confirm_email": "test@example.com",
        "password": "password123",
        "first_name": "Lily",
        "last_name": "Lorand",
        "age": "23",
        "neighborhood": "Bushwick",
        "pronouns": "she/her",
        "drinks": "yes",
        "smokes": "no",
    }

    user = create_user(data)

    assert user["email"] == "test@example.com"
    assert user["first_name"] == "Lily"
    assert user["last_initial"] == "L"
    assert user["age"] == 23
    assert user["neighborhood"] == "Bushwick"
    assert user["created_events"] == []
    assert user["joined_events"] == []


def test_create_user_hashes_password():
    data = {
        "email": "test@example.com",
        "confirm_email": "test@example.com",
        "password": "password123",
        "first_name": "Lily",
        "last_name": "Lorand",
        "age": "23",
        "neighborhood": "Bushwick",
    }

    user = create_user(data)

    assert user["password_hash"] != "password123"
    assert check_password_hash(user["password_hash"], "password123")