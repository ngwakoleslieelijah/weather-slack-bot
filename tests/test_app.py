import hashlib
import hmac
import time
from urllib.parse import urlencode

import pytest

import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    return app.app.test_client()


def signed_headers(body: str, secret: str = "test-secret"):
    timestamp = str(int(time.time()))
    base = f"v0:{timestamp}:{body}"
    signature = "v0=" + hmac.new(
        secret.encode(), base.encode(), hashlib.sha256
    ).hexdigest()
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
    }


def test_returns_temperature_for_city(client, monkeypatch):
    monkeypatch.setattr(
        app,
        "get_current_weather",
        lambda city: {"city": city, "temperature": 20.0, "temperature_f": 68.0},
    )
    body = urlencode({"text": "London"})

    response = client.post("/slack/commands", data=body, headers=signed_headers(body))

    assert response.status_code == 200
    assert response.json == {
        "response_type": "ephemeral",
        "text": "The current temperature in London is 20.0°C (68.0°F).",
    }


def test_requires_city(client):
    body = urlencode({"text": ""})

    response = client.post("/slack/commands", data=body, headers=signed_headers(body))

    assert response.status_code == 400
    assert "Usage" in response.json["text"]


def test_rejects_invalid_signature(client):
    body = urlencode({"text": "London"})
    headers = signed_headers(body, secret="wrong-secret")

    response = client.post("/slack/commands", data=body, headers=headers)

    assert response.status_code == 401
