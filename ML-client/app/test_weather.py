"""
Tests for weather.py — covers fetch_weather and fetch_weather_by_city.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_owm_response(temp=20.0, condition="clear sky", humidity=55, city="New York", icon="01d"):
    return {
        "main": {"temp": temp, "humidity": humidity},
        "weather": [{"description": condition, "icon": icon}],
        "name": city,
    }


# ── fetch_weather ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_weather_returns_weather_response():
    """fetch_weather should return a WeatherResponse on success."""
    data = _make_owm_response(temp=15.0, condition="light rain", humidity=80, city="London")

    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()

    with patch("weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from weather import fetch_weather
        result = await fetch_weather(lat=51.5, lon=-0.12)

    assert result.temp == 15.0
    assert result.condition == "light rain"
    assert result.humidity == 80
    assert result.city == "London"


@pytest.mark.asyncio
async def test_fetch_weather_raises_on_http_error():
    """fetch_weather should propagate HTTP errors."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock()
    )

    with patch("weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from weather import fetch_weather
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_weather(lat=0.0, lon=0.0)


# ── fetch_weather_by_city ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_weather_by_city_returns_weather_response():
    """fetch_weather_by_city should return a WeatherResponse on success."""
    data = _make_owm_response(temp=25.0, condition="sunny", humidity=40, city="Paris")

    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()

    with patch("weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from weather import fetch_weather_by_city
        result = await fetch_weather_by_city("Paris")

    assert result.temp == 25.0
    assert result.city == "Paris"


@pytest.mark.asyncio
async def test_fetch_weather_by_city_raises_on_http_error():
    """fetch_weather_by_city should propagate HTTP errors."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock()
    )

    with patch("weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from weather import fetch_weather_by_city
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_weather_by_city("FakeCity")
