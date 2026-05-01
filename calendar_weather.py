import calendar
import json
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import render_template, request


def register_calendar_weather_routes(app, db, login_required):
    @app.route("/calendar")
    @login_required
    def calendar_page():
        today = date.today()
        year = request.args.get("year", type=int) or today.year
        month = request.args.get("month", type=int) or today.month
        selected_city = request.args.get("city", "New York City").strip() or "New York City"

        if month < 1 or month > 12:
            year, month = today.year, today.month

        month_start = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        month_end = date(year, month, last_day)

        exams = list(db.exams.find({
            "exam_date": {
                "$gte": month_start.isoformat(),
                "$lte": month_end.isoformat()
            }
        }))
        preparations = list(db.preparations.find({
            "preparation_date": {
                "$gte": month_start.isoformat(),
                "$lte": month_end.isoformat()
            }
        }))

        exams_by_day = {}
        for exam in exams:
            exam["_id"] = str(exam["_id"])
            exams_by_day.setdefault(exam["exam_date"], []).append(exam)

        exam_lookup = {}
        for exam in db.exams.find({}, {"subject": 1, "exam_type": 1, "exam_date": 1}):
            exam_lookup[str(exam["_id"])] = exam

        preparations_by_day = {}
        for preparation in preparations:
            preparation["_id"] = str(preparation["_id"])
            preparation["exam_id"] = str(preparation["exam_id"])
            preparation["exam"] = exam_lookup.get(preparation["exam_id"])
            preparation["completed"] = preparation.get("completed", False)
            preparations_by_day.setdefault(preparation["preparation_date"], []).append(preparation)

        weather_by_day = {}
        weather_error = None
        resolved_city = selected_city

        try:
            city_result = geocode_us_city(selected_city)
            if city_result:
                resolved_city = city_result.get("name", selected_city)
                admin1 = city_result.get("admin1")
                if admin1:
                    resolved_city = f"{resolved_city}, {admin1}"

                latitude = city_result["latitude"]
                longitude = city_result["longitude"]

                if month_start < today:
                    historical_end = min(month_end, today - timedelta(days=1))
                    if historical_end >= month_start:
                        weather_by_day.update(
                            fetch_historical_daily_weather(
                                latitude,
                                longitude,
                                month_start.isoformat(),
                                historical_end.isoformat()
                            )
                        )

                if month_end >= today:
                    weather_by_day.update(fetch_daily_weather(latitude, longitude))
            else:
                weather_error = "City not found."
        except Exception:
            weather_error = "Weather is unavailable right now."

        month_weeks = []
        month_calendar = calendar.Calendar(firstweekday=6)
        for week in month_calendar.monthdatescalendar(year, month):
            week_days = []
            for day in week:
                day_key = day.isoformat()
                weather = weather_by_day.get(day_key)
                day_preparations = preparations_by_day.get(day_key, [])

                for preparation in day_preparations:
                    preparation["weather_alert"] = (
                        preparation.get("location") == "Outdoor"
                        and is_inclement_weather(weather)
                    )
                    preparation["is_past_due"] = (
                        not preparation.get("completed", False)
                        and day < today
                    )

                week_days.append({
                    "date": day,
                    "day_number": day.day,
                    "is_current_month": day.month == month,
                    "is_today": day == today,
                    "exams": exams_by_day.get(day_key, []),
                    "preparations": day_preparations,
                    "weather": weather,
                    "weather_label": weather.get("label") if weather else None
                })
            month_weeks.append(week_days)

        prev_year, prev_month = shift_month(year, month, -1)
        next_year, next_month = shift_month(year, month, 1)

        return render_template(
            "calendar.html",
            month_label=month_start.strftime("%B %Y"),
            month_weeks=month_weeks,
            selected_city=selected_city,
            resolved_city=resolved_city,
            weather_error=weather_error,
            prev_year=prev_year,
            prev_month=prev_month,
            next_year=next_year,
            next_month=next_month
        )


def shift_month(year, month, offset):
    total_months = year * 12 + (month - 1) + offset
    return total_months // 12, total_months % 12 + 1


def fetch_json(url, params):
    query = urlencode(params)
    request = Request(
        f"{url}?{query}",
        headers={"User-Agent": "StudyCast/1.0 (student project)"}
    )
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def fetch_json_absolute(url):
    request = Request(
        url,
        headers={"User-Agent": "StudyCast/1.0 (student project)"}
    )
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def geocode_us_city(city_name):
    payload = fetch_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {
            "name": city_name,
            "count": 1,
            "language": "en",
            "format": "json",
            "countryCode": "US"
        }
    )
    results = payload.get("results") or []
    return results[0] if results else None


def fetch_daily_weather(latitude, longitude):
    points_payload = fetch_json_absolute(
        f"https://api.weather.gov/points/{latitude},{longitude}"
    )
    forecast_url = points_payload.get("properties", {}).get("forecast")
    if not forecast_url:
        return {}

    forecast_payload = fetch_json_absolute(forecast_url)
    periods = forecast_payload.get("properties", {}).get("periods") or []

    weather_by_day = {}
    for period in periods:
        day = period.get("startTime", "")[:10]
        if not day:
            continue

        day_weather = weather_by_day.setdefault(day, {
            "label": None,
            "temp_max": None,
            "temp_min": None,
            "short_forecasts": []
        })

        short_forecast = period.get("shortForecast")
        if short_forecast:
            day_weather["short_forecasts"].append(short_forecast)
            if day_weather["label"] is None or period.get("isDaytime"):
                day_weather["label"] = short_forecast

        temperature = period.get("temperature")
        if isinstance(temperature, (int, float)):
            if period.get("isDaytime"):
                current_max = day_weather["temp_max"]
                day_weather["temp_max"] = temperature if current_max is None else max(current_max, temperature)
            else:
                current_min = day_weather["temp_min"]
                day_weather["temp_min"] = temperature if current_min is None else min(current_min, temperature)

    return weather_by_day


def fetch_historical_daily_weather(latitude, longitude, start_date, end_date):
    payload = fetch_json(
        "https://archive-api.open-meteo.com/v1/archive",
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "America/New_York"
        }
    )

    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    weather_codes = daily.get("weather_code") or []
    temp_max = daily.get("temperature_2m_max") or []
    temp_min = daily.get("temperature_2m_min") or []

    weather_by_day = {}
    for index, day in enumerate(times):
        weather_by_day[day] = {
            "label": describe_historical_weather(weather_codes[index]),
            "temp_max": temp_max[index],
            "temp_min": temp_min[index],
            "weather_code": weather_codes[index]
        }

    return weather_by_day


def describe_historical_weather(weather_code):
    if weather_code == 0:
        return "Clear"
    if weather_code in {1, 2, 3}:
        return "Cloudy"
    if weather_code in {45, 48}:
        return "Fog"
    if weather_code in {51, 53, 55, 56, 57}:
        return "Drizzle"
    if weather_code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "Rain"
    if weather_code in {71, 73, 75, 77, 85, 86}:
        return "Snow"
    if weather_code in {95, 96, 99}:
        return "Storm"
    return "Weather"


def is_inclement_weather(weather):
    if not weather:
        return False

    weather_code = weather.get("weather_code")
    if weather_code is not None:
        return weather_code in {
            51, 53, 55, 56, 57,
            61, 63, 65, 66, 67,
            71, 73, 75, 77,
            80, 81, 82, 85, 86,
            95, 96, 99
        }

    forecast_text = " ".join(weather.get("short_forecasts", [])).lower()
    bad_weather_terms = [
        "rain",
        "drizzle",
        "showers",
        "thunderstorm",
        "snow",
        "sleet",
        "freezing",
        "ice",
        "hail",
        "wintry"
    ]
    return any(term in forecast_text for term in bad_weather_terms)
