# Crypto Telegram Alert Bot

A lightweight Telegram bot that reads live cryptocurrency prices from Binance's public API and sends one-time price alerts. Configure a Telegram token, install the dependencies, and run it locally with `python -m src.bot`—no exchange account or trading permissions required.

## Features

- `/price BTCUSDT` — fetch the latest public spot price
- `/alert BTCUSDT 70000` — create a one-time target-price alert
- `/list` — show active alerts and their IDs
- `/cancel <alert_id|all>` — cancel one alert or all alerts
- Asynchronous market requests and background alert monitoring
- Graceful shutdown, structured logging, and deterministic mocked tests

## Quick Start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/naomi197/crypto-telegram-alert-bot.git
cd crypto-telegram-alert-bot
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set `TELEGRAM_BOT_TOKEN` in `.env` using a token created with Telegram's `@BotFather`, then start the bot:

```bash
python -m src.bot
```

## Architecture

```text
Telegram commands -> Bot handlers -> Alert store
                                  |        |
                           Alert worker -> Binance public REST API
```

- `src/config.py` loads and validates environment settings
- `src/market.py` handles asynchronous market-data requests
- `src/alerts.py` manages alerts and the polling worker
- `src/bot.py` registers commands and controls startup and shutdown

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Required | Telegram bot token from BotFather |
| `BINANCE_BASE_URL` | `https://api.binance.com` | Public market API base URL |
| `POLL_INTERVAL_SECONDS` | `15` | Alert-check interval |
| `REQUEST_TIMEOUT_SECONDS` | `10` | HTTP request timeout |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Testing

Tests use mocked market responses and do not require network access or a Telegram token.

```bash
pytest tests
```

## Safety

The bot only reads public market data. It cannot place trades, withdraw funds, or access private exchange data. Alerts are stored in memory and reset when the process stops.

## License

This project is available under the MIT License. See `LICENSE` for details.
