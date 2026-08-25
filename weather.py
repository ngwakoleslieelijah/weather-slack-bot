import os

import requests


class WeatherError(Exception):
    """An expected error while fetching weather data."""


def get_current_weather(city: str) -> dict:
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    if not api_key:
        raise WeatherError("The weather service is not configured yet.")

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        if getattr(error.response, "status_code", None) == 404:
            raise WeatherError(f"I could not find a city named {city}.") from error
        raise WeatherError("The weather service is unavailable right now.") from error

    data = response.json()
    try:
        temperature = float(data["main"]["temp"])
        city_name = data["name"]
    except (KeyError, TypeError, ValueError) as error:
        raise WeatherError("The weather service returned an unexpected response.") from error

    return {
        "city": city_name,
        "temperature": temperature,
        "temperature_f": temperature * 9 / 5 + 32,
    }
