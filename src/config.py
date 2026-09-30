"""Validated environment-backed application settings."""
from dataclasses import dataclass
import os

try:
    from dotenv import load_dotenv
except ImportError:  # Environment variables also work without python-dotenv.
    load_dotenv = None


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    binance_base_url: str = "https://api.binance.com"
    poll_interval_seconds: float = 15.0
    request_timeout_seconds: float = 10.0
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        if load_dotenv is not None:
            load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token or token == "replace_me":
            raise ValueError("TELEGRAM_BOT_TOKEN is required; copy .env.example to .env")
        try:
            poll = float(os.getenv("POLL_INTERVAL_SECONDS", "15"))
            timeout = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
        except ValueError as exc:
            raise ValueError("Poll interval and request timeout must be numbers") from exc
        if poll <= 0 or timeout <= 0:
            raise ValueError("Poll interval and request timeout must be positive")
        base_url = os.getenv("BINANCE_BASE_URL", "https://api.binance.com").strip().rstrip("/")
        if not base_url.startswith(("https://", "http://")):
            raise ValueError("BINANCE_BASE_URL must be an HTTP(S) URL")
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        if not hasattr(__import__("logging"), level):
            raise ValueError("LOG_LEVEL must be a standard logging level")
        return cls(token, base_url, poll, timeout, level)
