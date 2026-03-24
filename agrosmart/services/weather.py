from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


class WeatherError(RuntimeError):
    pass


def fetch_openweather_current(location: str) -> dict:
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise WeatherError("OPENWEATHER_API_KEY is not set.")

    q = urllib.parse.quote(location)
    geo_url = f"https://api.openweathermap.org/geo/1.0/direct?q={q}&limit=1&appid={api_key}"
    geo = _get_json(geo_url)
    if not geo:
        raise WeatherError("Location not found.")

    lat = geo[0]["lat"]
    lon = geo[0]["lon"]

    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={api_key}"
    data = _get_json(weather_url)

    main = data.get("main", {}) or {}
    rain = data.get("rain", {}) or {}
    return {
        "provider": "openweather",
        "location": location,
        "lat": lat,
        "lon": lon,
        "temperature_c": main.get("temp"),
        "humidity_pct": main.get("humidity"),
        "rain_1h_mm": rain.get("1h", 0.0) if isinstance(rain, dict) else 0.0,
        "rain_3h_mm": rain.get("3h", 0.0) if isinstance(rain, dict) else 0.0,
    }


def _get_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "AgroSmart/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload)
    except Exception as exc:
        raise WeatherError(str(exc)) from exc

