# Crypto Telegram Alert Bot

A lightweight, read-only Telegram bot for live cryptocurrency prices and one-shot price alerts. It uses Python's `asyncio`, `aiohttp`, and `python-telegram-bot`; market data comes from Binance's public REST API. No exchange credentials or trading permissions are required.

## Features

- `/price BTCUSDT` — fetch the latest public spot price.
- `/alert BTCUSDT 70000` — create a one-shot alert when the price reaches or exceeds a target.
- `/list` — display your active alerts and their IDs.
- `/cancel [alert_id|all]` — cancel one alert or all of your alerts.
- Async market requests, an asynchronous alert worker, graceful shutdown, and standard-library logging.
- In-memory alert storage and deterministic tests using mocked HTTP/market clients.

> **Safety:** This project only reads public market data. It cannot place trades, withdraw funds, or access private account data. Alerts are held in memory and are lost when the process stops.

## Architecture

```text
Telegram updates -> python-telegram-bot handlers -> AlertStore
                                                  |       |
                                      AlertWorker +---- AsyncMarketClient -> Binance REST
```

- `src/config.py` loads and validates environment settings.
- `src/market.py` owns the read-only `aiohttp` client and ticker parsing.
- `src/alerts.py` provides a concurrency-safe in-memory store and polling worker.
- `src/bot.py` wires the Telegram commands and manages startup/shutdown.

## Quickstart

Requires Python 3.10 or newer.

```bash
git clone <your-repository-url>
cd crypto-telegram-alert-bot
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set `TELEGRAM_BOT_TOKEN` in `.env` to a token created with [@BotFather](https://t.me/BotFather), then run:

```bash
python -m src.bot
```

Never commit `.env` or share your bot token. No Binance API key is needed.

## Testing

Tests use mocked market responses; they do not make network calls and do not require a Telegram token.

```bash
pytest tests
```

## Configuration

| Variable | Default | Description |
|---|---:|---|
| `TELEGRAM_BOT_TOKEN` | required | Telegram bot token from BotFather |
| `BINANCE_BASE_URL` | `https://api.binance.com` | Public market API base URL |
| `POLL_INTERVAL_SECONDS` | `15` | Alert check interval |
| `REQUEST_TIMEOUT_SECONDS` | `10` | HTTP request timeout |
| `LOG_LEVEL` | `INFO` | Standard Python logging level |

## License

This project is provided under the MIT License. See [LICENSE](LICENSE).
