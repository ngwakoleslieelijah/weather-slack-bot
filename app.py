import hashlib
import hmac
import os
import time
from urllib.parse import parse_qs

from flask import Flask, jsonify, request

from weather import WeatherError, get_current_weather

app = Flask(__name__)


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
        weather = get_current_weather(city)
    except WeatherError as error:
        return slack_response(str(error), 400)

    return slack_response(
        f"The current temperature in {weather['city']} is "
        f"{weather['temperature']:.1f}°C ({weather['temperature_f']:.1f}°F)."
    )


@app.get("/")
def index():
    return """
    <html>
        <head><title>Jumo Weather Slack Bot</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1>🌤️ Jumo Weather Slack Bot</h1>
            <p>This service powers the <code>/jumo_weather [city]</code> Slack slash command.</p>
            <h2>Available Endpoints:</h2>
            <ul>
                <li><strong>GET /health</strong> - Health check endpoint</li>
                <li><strong>POST /slack/commands</strong> - Slack slash command handler</li>
            </ul>
            <h2>Usage in Slack:</h2>
            <pre>/jumo_weather London</pre>
            <p>Returns the current temperature in the specified city.</p>
        </body>
    </html>
    """


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.errorhandler(WeatherError)
def handle_weather_error(error):
    return slack_response(str(error), 400)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")))
