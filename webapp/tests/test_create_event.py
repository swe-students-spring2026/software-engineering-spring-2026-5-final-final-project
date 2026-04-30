from datetime import datetime

from models.event_model import create_event
from utils.validation import validate_event


def valid_event_data():
    return {
        "title": "Dinner",
        "description": "Fun dinner",
        "date": "2026-05-01",
        "time": "18:00",
        "capacity": "4",
        "tags": ["food", "casual"],
        "location": "NYC",
    }


def test_create_event_success():
    data = {
        "title": "Pizza Night",
        "description": "Come eat pizza",
        "date": "2026-05-01",
        "time": "19:00",
        "capacity": "6",
        "tags": ["pizza", "casual"],
        "location": "NYC",
    }

    host_id = "user123"

    event = create_event(data, host_id)

    assert event["title"] == "Pizza Night"
    assert event["description"] == "Come eat pizza"
    assert event["date"] == "2026-05-01"
    assert event["time"] == "19:00"
    assert event["host_id"] == host_id
    assert event["capacity"] == 6
    assert event["tags"] == ["pizza", "casual"]
    assert event["attendees"] == [host_id]
    assert event["image_url"] is None
    assert isinstance(event["created_at"], datetime)
    assert isinstance(event["updated_at"], datetime)


def test_create_event_with_image_url():
    data = valid_event_data()

    event = create_event(data, "user123", image_url="/uploads/dinner.jpg")

    assert event["image_url"] == "/uploads/dinner.jpg"


def test_validate_event_missing_title():
    data = valid_event_data()
    data["title"] = ""

    error = validate_event(data)

    assert error == "title is required."


def test_validate_event_missing_date():
    data = valid_event_data()
    data["date"] = ""

    error = validate_event(data)

    assert error == "date is required."


def test_validate_event_missing_location():
    data = valid_event_data()
    data["location"] = ""

    error = validate_event(data)

    assert error == "location is required."


def test_validate_event_missing_description():
    data = valid_event_data()
    data["description"] = ""

    error = validate_event(data)

    assert error == "description is required."


def test_validate_event_capacity_too_low():
    data = valid_event_data()
    data["capacity"] = "1"

    error = validate_event(data)

    assert error == "Capacity must be at least 3."


def test_validate_event_too_many_tags():
    data = valid_event_data()
    data["tags"] = ["food", "casual", "music", "games"]

    error = validate_event(data)

    assert error == "You can select up to 3 tags only."


def test_validate_event_success():
    data = valid_event_data()

    error = validate_event(data)

    assert error is None