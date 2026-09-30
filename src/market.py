"""Async read-only client for Binance public ticker data."""
from dataclasses import dataclass
import math
from typing import Any

import aiohttp


@dataclass(frozen=True, slots=True)
class Ticker:
    symbol: str
    price: float


class AsyncMarketClient:
    """Fetch spot prices from Binance's public ticker endpoint.

    An injected session remains caller-owned; otherwise this client creates and
    closes its own session through the async context-manager interface.
    """
    def __init__(self, base_url: str = "https://api.binance.com",
                 timeout_seconds: float = 10.0, session: Any | None = None):
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "AsyncMarketClient":
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
            )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        value = symbol.strip().upper().replace("/", "")
        if not value or not value.isalnum():
            raise ValueError("Symbol must contain letters and numbers only")
        return value

    async def get_price(self, symbol: str) -> Ticker:
        normalized = self.normalize_symbol(symbol)
        if self._session is None:
            raise RuntimeError("Use AsyncMarketClient as an async context manager")
        url = f"{self.base_url}/api/v3/ticker/price"
        async with self._session.get(url, params={"symbol": normalized}) as response:
            response.raise_for_status()
            payload = await response.json()
        try:
            result_symbol = self.normalize_symbol(payload["symbol"])
            price = float(payload["price"])
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ValueError("Unexpected ticker response from market API") from exc
        if result_symbol != normalized or not math.isfinite(price) or price <= 0:
            raise ValueError("Market API returned an invalid ticker")
        return Ticker(symbol=result_symbol, price=price)


# Backwards-compatible spelling for users of the initial sample implementation.
MarketClient = AsyncMarketClient
