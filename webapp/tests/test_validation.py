from utils.validation import validate_signup, validate_login
from werkzeug.security import generate_password_hash


class FakeUsersCollection:
    def __init__(self, existing_user=None):
        self.existing_user = existing_user

    def find_one(self, query):
        return self.existing_user


def test_validate_signup_success():
    data = {
        "email": "test@example.com",
        "confirm_email": "test@example.com",
        "password": "password123",
        "confirm_password": "password123",
        "first_name": "Lily",
        "last_name": "Lorand",
        "age": "23",
        "neighborhood": "Bushwick",
    }

    users_collection = FakeUsersCollection()

    assert validate_signup(data, users_collection) is None


def test_validate_signup_missing_required_field():
    data = {
        "email": "",
        "confirm_email": "test@example.com",
        "password": "password123",
        "confirm_password": "password123",
        "first_name": "Lily",
        "last_name": "Lorand",
        "age": "23",
        "neighborhood": "Bushwick",
    }

    users_collection = FakeUsersCollection()

    assert validate_signup(data, users_collection) == "Please fill out all required fields."


def test_validate_signup_passwords_do_not_match():
    data = {
        "email": "test@example.com",
        "confirm_email": "test@example.com",
        "password": "password123",
        "confirm_password": "different",
        "first_name": "Lily",
        "last_name": "Lorand",
        "age": "23",
        "neighborhood": "Bushwick",
    }

    users_collection = FakeUsersCollection()

    assert validate_signup(data, users_collection) == "Passwords do not match."


def test_validate_signup_existing_user():
    data = {
        "email": "test@example.com",
        "confirm_email": "test@example.com",
        "password": "password123",
        "confirm_password": "password123",
        "first_name": "Lily",
        "last_name": "Lorand",
        "age": "23",
        "neighborhood": "Bushwick",
    }

    users_collection = FakeUsersCollection(existing_user={"email": "test@example.com"})

    assert validate_signup(data, users_collection) == "An account with this email already exists."

def test_validate_login_success():
    data = {
        "email": "test@example.com",
        "password": "password123",
    }

    stored_user = {
        "email": "test@example.com",
        "password_hash": generate_password_hash("password123"),
    }

    users_collection = FakeUsersCollection(existing_user=stored_user)

    error, user = validate_login(data, users_collection)

    assert error is None
    assert user == stored_user


def test_validate_login_missing_email_or_password():
    data = {
        "email": "",
        "password": "password123",
    }

    users_collection = FakeUsersCollection()

    error, user = validate_login(data, users_collection)

    assert error == "Please enter email and password."
    assert user is None


def test_validate_login_user_not_found():
    data = {
        "email": "missing@example.com",
        "password": "password123",
    }

    users_collection = FakeUsersCollection()

    error, user = validate_login(data, users_collection)

    assert error == "No account found with that email."
    assert user is None


def test_validate_login_wrong_password():
    data = {
        "email": "test@example.com",
        "password": "wrongpassword",
    }

    stored_user = {
        "email": "test@example.com",
        "password_hash": generate_password_hash("password123"),
    }

    users_collection = FakeUsersCollection(existing_user=stored_user)

    error, user = validate_login(data, users_collection)

    assert error == "Incorrect password."
    assert user is None