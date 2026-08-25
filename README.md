# Jumo Weather Slack Bot

A Flask service that powers the `/jumo_weather [city]` Slack slash command using the OpenWeather current weather API.

## Setup

1. Create a free account at [OpenWeather](https://openweathermap.org/), create an API key, and wait for the key to activate.
2. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps), then add a Slash Command named `/jumo_weather`.
3. Set the command request URL to `https://YOUR-NGROK-DOMAIN.ngrok-free.app/slack/commands` after starting ngrok below. Copy the app's **Signing Secret**.
4. Create a virtual environment and install dependencies:

	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt
	```

5. Create `.env` from `.env.example` and fill in both secrets. Load it in your shell before starting the app:

	```bash
	set -a
	source .env
	set +a
	python app.py
	```

6. In another terminal, expose the local service with ngrok:

	```bash
	ngrok http 3000
	```

	Use the HTTPS forwarding URL in the Slack command configuration. Slack may send a verification request when you save it; the endpoint is ready for POST requests from Slack.

## Use

In Slack, run:

```text
/jumo_weather London
```

The bot replies privately with the current temperature in Celsius and Fahrenheit.

## Test

```bash
pytest
```

The tests mock the weather response and cover a successful command, missing city, and invalid Slack signature. API keys and Slack secrets are read only from environment variables and should never be committed.
