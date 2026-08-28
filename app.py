import hashlib
import hmac
import os
import time
from urllib.parse import parse_qs
from typing import TypedDict, cast

from flask import Flask, jsonify, request

from weather import WeatherError, get_current_weather  # type: ignore[reportUnknownVariableType]

app = Flask(__name__)


class CurrentWeather(TypedDict):
    city: str
    temperature: float
    temperature_f: float


def verify_slack_signature(raw_body: bytes, timestamp: str, signature: str) -> bool:
    signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
    if not signing_secret or not timestamp or not signature:
        return False

    try:
        request_age = abs(time.time() - int(timestamp))
    except ValueError:
        return False

    if request_age > 60 * 5:
        return False

    basestring = f"v0:{timestamp}:{raw_body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        signing_secret.encode("utf-8"),
        basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def slack_response(text: str, status_code: int = 200):
    return jsonify({"response_type": "ephemeral", "text": text}), status_code


@app.post("/slack/commands")
def slack_command():
    if not verify_slack_signature(
        request.get_data(),
        request.headers.get("X-Slack-Request-Timestamp", ""),
        request.headers.get("X-Slack-Signature", ""),
    ):
        return slack_response("Invalid Slack request signature.", 401)

    form = parse_qs(request.get_data(as_text=True))
    city = form.get("text", [""])[0].strip()
    if not city:
        return slack_response("Usage: /jumo_weather <city>", 400)

    try:
        weather = cast(CurrentWeather, get_current_weather(city))
    except WeatherError as error:
        return slack_response(str(error), 400)

    return slack_response(
        f"The current temperature in {weather['city']} is "
        f"{weather['temperature']:.1f}°C ({weather['temperature_f']:.1f}°F)."
    )


@app.get("/")
def index():
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Jumo Weather Slack Bot</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
              rel="stylesheet">
    </head>
    <body class="bg-light">
        <main class="container py-5">
            <div class="card shadow-sm mx-auto" style="max-width: 720px;">
                <div class="card-body p-4">
                    <h1 class="card-title text-primary">🌤️ Jumo Weather Slack Bot</h1>
                    <p class="lead">
                        This service powers the
                        <code>/jumo_weather [city]</code> Slack slash command.
                    </p>

                    <h2 class="h4 mt-4">Available Endpoints</h2>
                    <ul class="list-group mb-4">
                        <li class="list-group-item">
                            <strong>GET /health</strong> — Health check endpoint
                        </li>
                        <li class="list-group-item">
                            <strong>POST /slack/commands</strong> — Slack command handler
                        </li>
                    </ul>

                    <div class="alert alert-info">
                        <strong>Usage:</strong>
                        <code>/jumo_weather London</code>
                    </div>

                    <p class="text-muted mb-0">
                        Returns the current temperature for the specified city.
                    </p>
                </div>
            </div>
        </main>
    </body>
    </html>
    """


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.errorhandler(WeatherError)
def handle_weather_error(error: WeatherError):
    return slack_response(str(error), 400)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")))
