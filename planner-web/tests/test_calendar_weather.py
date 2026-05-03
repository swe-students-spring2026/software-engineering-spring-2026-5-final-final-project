import json
import sys
from datetime import date as real_date
from pathlib import Path

import mongomock
import pytest
from bson.objectid import ObjectId
from flask import Flask


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import calendar_weather


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FixedDate(real_date):
    @classmethod
    def today(cls):
        return cls(2026, 5, 15)


def make_calendar_client(monkeypatch, database, captured_context):
    test_app = Flask(__name__)
    test_app.secret_key = "test-secret"

    def login_required(view_func):
        return view_func

    def fake_render(template, **context):
        captured_context["template"] = template
        captured_context.update(context)
        return "calendar rendered"

    monkeypatch.setattr(calendar_weather, "render_template", fake_render)
    calendar_weather.register_calendar_weather_routes(test_app, database, login_required)
    return test_app.test_client()


def test_shift_month_handles_year_boundaries():
    assert calendar_weather.shift_month(2026, 1, -1) == (2025, 12)
    assert calendar_weather.shift_month(2026, 12, 1) == (2027, 1)
    assert calendar_weather.shift_month(2026, 5, 0) == (2026, 5)


def test_fetch_json_uses_params_and_user_agent(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["agent"] = request.get_header("User-agent")
        captured["timeout"] = timeout
        return JsonResponse({"ok": True})

    monkeypatch.setattr(calendar_weather, "urlopen", fake_urlopen)
    payload = calendar_weather.fetch_json("https://example.test/search", {"name": "New York"})

    assert payload == {"ok": True}
    assert "name=New+York" in captured["url"]
    assert captured["agent"] == "StudyCast/1.0 (student project)"
    assert captured["timeout"] == 5


def test_fetch_json_absolute_uses_url(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return JsonResponse({"absolute": True})

    monkeypatch.setattr(calendar_weather, "urlopen", fake_urlopen)
    assert calendar_weather.fetch_json_absolute("https://example.test/weather") == {"absolute": True}
    assert captured == {"url": "https://example.test/weather", "timeout": 5}


def test_geocode_us_city_returns_first_result_or_none(monkeypatch):
    monkeypatch.setattr(
        calendar_weather,
        "fetch_json",
        lambda url, params: {"results": [{"name": "Brooklyn", "latitude": 1, "longitude": 2}]},
    )
    assert calendar_weather.geocode_us_city("Brooklyn")["name"] == "Brooklyn"

    monkeypatch.setattr(calendar_weather, "fetch_json", lambda url, params: {})
    assert calendar_weather.geocode_us_city("Nowhere") is None


def test_fetch_daily_weather_combines_day_and_night_periods(monkeypatch):
    def fake_fetch_absolute(url):
        if "points" in url:
            return {"properties": {"forecast": "https://forecast.test/grid"}}
        return {
            "properties": {
                "periods": [
                    {
                        "startTime": "2026-05-15T08:00:00-04:00",
                        "shortForecast": "Sunny",
                        "temperature": 72,
                        "isDaytime": True,
                    },
                    {
                        "startTime": "2026-05-15T20:00:00-04:00",
                        "shortForecast": "Rain showers",
                        "temperature": 55,
                        "isDaytime": False,
                    },
                    {
                        "startTime": "2026-05-16T08:00:00-04:00",
                        "shortForecast": "Warm",
                        "temperature": 80,
                        "isDaytime": True,
                    },
                    {
                        "startTime": "2026-05-16T12:00:00-04:00",
                        "shortForecast": "Hot",
                        "temperature": 84,
                        "isDaytime": True,
                    },
                    {"startTime": "", "shortForecast": "Ignored", "temperature": 10},
                ]
            }
        }

    monkeypatch.setattr(calendar_weather, "fetch_json_absolute", fake_fetch_absolute)
    weather = calendar_weather.fetch_daily_weather(40.0, -73.0)

    assert weather["2026-05-15"]["label"] == "Sunny"
    assert weather["2026-05-15"]["temp_max"] == 72
    assert weather["2026-05-15"]["temp_min"] == 55
    assert weather["2026-05-16"]["temp_max"] == 84


def test_fetch_daily_weather_returns_empty_without_forecast(monkeypatch):
    monkeypatch.setattr(
        calendar_weather,
        "fetch_json_absolute",
        lambda url: {"properties": {}},
    )
    assert calendar_weather.fetch_daily_weather(40.0, -73.0) == {}


def test_fetch_historical_daily_weather_maps_archive_payload(monkeypatch):
    monkeypatch.setattr(
        calendar_weather,
        "fetch_json",
        lambda url, params: {
            "daily": {
                "time": ["2026-05-01", "2026-05-02"],
                "weather_code": [0, 63],
                "temperature_2m_max": [70, 60],
                "temperature_2m_min": [50, 45],
            }
        },
    )

    weather = calendar_weather.fetch_historical_daily_weather(
        40.0,
        -73.0,
        "2026-05-01",
        "2026-05-02",
    )

    assert weather["2026-05-01"]["label"] == "Clear"
    assert weather["2026-05-02"]["label"] == "Rain"
    assert weather["2026-05-02"]["temp_min"] == 45


@pytest.mark.parametrize(
    ("code", "label"),
    [
        (0, "Clear"),
        (2, "Cloudy"),
        (45, "Fog"),
        (53, "Drizzle"),
        (63, "Rain"),
        (73, "Snow"),
        (96, "Storm"),
        (999, "Weather"),
    ],
)
def test_describe_historical_weather(code, label):
    assert calendar_weather.describe_historical_weather(code) == label


@pytest.mark.parametrize(
    ("weather", "expected"),
    [
        (None, False),
        ({"weather_code": 63}, True),
        ({"weather_code": 0}, False),
        ({"short_forecasts": ["Clear skies"]}, False),
        ({"short_forecasts": ["Rain showers late"]}, True),
        ({"short_forecasts": ["Wintry mix"]}, True),
    ],
)
def test_is_inclement_weather(weather, expected):
    assert calendar_weather.is_inclement_weather(weather) is expected


def test_calendar_page_builds_month_context_and_weather_alerts(monkeypatch):
    monkeypatch.setattr(calendar_weather, "date", FixedDate)
    database = mongomock.MongoClient().studycast
    exam_id = database.exams.insert_one({
        "subject": "Math",
        "exam_type": "Final",
        "exam_date": "2026-05-20",
    }).inserted_id
    database.preparations.insert_one({
        "exam_id": exam_id,
        "preparation_date": "2026-05-10",
        "difficulty": "Light (~1 hr)",
        "location": "Outdoor",
        "completed": False,
    })

    monkeypatch.setattr(
        calendar_weather,
        "geocode_us_city",
        lambda city: {
            "name": "Boston",
            "admin1": "Massachusetts",
            "latitude": 42.3,
            "longitude": -71.1,
        },
    )
    monkeypatch.setattr(
        calendar_weather,
        "fetch_historical_daily_weather",
        lambda *args: {
            "2026-05-10": {
                "label": "Rain",
                "weather_code": 63,
                "temp_max": 60,
                "temp_min": 50,
            }
        },
    )
    monkeypatch.setattr(
        calendar_weather,
        "fetch_daily_weather",
        lambda *args: {
            "2026-05-20": {
                "label": "Sunny",
                "short_forecasts": ["Sunny"],
                "temp_max": 76,
                "temp_min": 58,
            }
        },
    )
    captured_context = {}
    client = make_calendar_client(monkeypatch, database, captured_context)

    response = client.get("/calendar?year=2026&month=5&city=Boston")

    assert response.status_code == 200
    assert captured_context["template"] == "calendar.html"
    assert captured_context["month_label"] == "May 2026"
    assert captured_context["resolved_city"] == "Boston, Massachusetts"
    assert captured_context["prev_month"] == 4
    assert captured_context["next_month"] == 6

    days = [day for week in captured_context["month_weeks"] for day in week]
    prep_day = next(day for day in days if day["date"].isoformat() == "2026-05-10")
    assert prep_day["preparations"][0]["weather_alert"] is True
    assert prep_day["preparations"][0]["is_past_due"] is True

    exam_day = next(day for day in days if day["date"].isoformat() == "2026-05-20")
    assert exam_day["exams"][0]["subject"] == "Math"
    assert exam_day["weather_label"] == "Sunny"


def test_calendar_page_handles_invalid_month_and_unknown_city(monkeypatch):
    monkeypatch.setattr(calendar_weather, "date", FixedDate)
    database = mongomock.MongoClient().studycast
    monkeypatch.setattr(calendar_weather, "geocode_us_city", lambda city: None)
    captured_context = {}
    client = make_calendar_client(monkeypatch, database, captured_context)

    response = client.get("/calendar?year=2026&month=99&city=%20")

    assert response.status_code == 200
    assert captured_context["month_label"] == "May 2026"
    assert captured_context["selected_city"] == "New York City"
    assert captured_context["weather_error"] == "City not found."


def test_calendar_page_handles_weather_exception(monkeypatch):
    monkeypatch.setattr(calendar_weather, "date", FixedDate)
    database = mongomock.MongoClient().studycast

    def broken_geocoder(city):
        raise RuntimeError("weather api down")

    monkeypatch.setattr(calendar_weather, "geocode_us_city", broken_geocoder)
    captured_context = {}
    client = make_calendar_client(monkeypatch, database, captured_context)

    response = client.get("/calendar?year=2026&month=5&city=Queens")

    assert response.status_code == 200
    assert captured_context["weather_error"] == "Weather is unavailable right now."
