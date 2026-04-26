import httpx
from schemas import WeatherResponse
from config import settings

OWM_BASE = "https://api.openweathermap.org/data/2.5/weather"


async def fetch_weather(lat: float, lon: float) -> WeatherResponse:
    """Fetch current weather for a lat/lon from OpenWeatherMap."""
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.openweather_api_key,
        "units": "metric",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(OWM_BASE, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

    return WeatherResponse(
        temp=data["main"]["temp"],
        condition=data["weather"][0]["description"],
        humidity=data["main"]["humidity"],
        city=data.get("name", ""),
        icon=data["weather"][0]["icon"],
    )


async def fetch_weather_by_city(city: str) -> WeatherResponse:
    """Fetch current weather by city name."""
    params = {
        "q": city,
        "appid": settings.openweather_api_key,
        "units": "metric",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(OWM_BASE, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

    return WeatherResponse(
        temp=data["main"]["temp"],
        condition=data["weather"][0]["description"],
        humidity=data["main"]["humidity"],
        city=data.get("name", ""),
        icon=data["weather"][0]["icon"],
    )