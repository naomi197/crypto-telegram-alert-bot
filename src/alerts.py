"""Concurrency-safe in-memory alert store and asynchronous polling worker."""
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Alert:
    alert_id: int
    chat_id: int
    symbol: str
    target_price: float


class PriceClient(Protocol):
    async def get_price(self, symbol: str): ...


class AlertStore:
    """Store one-shot alerts in memory; alert IDs are unique for this process."""
    def __init__(self) -> None:
        self._alerts: dict[int, Alert] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def add(self, chat_id: int, symbol: str, target_price: float) -> Alert:
        async with self._lock:
            alert = Alert(self._next_id, chat_id, symbol, target_price)
            self._next_id += 1
            self._alerts[alert.alert_id] = alert
            return alert

    async def list_for(self, chat_id: int) -> list[Alert]:
        async with self._lock:
            return [a for a in self._alerts.values() if a.chat_id == chat_id]

    async def remove(self, alert: Alert | int) -> bool:
        alert_id = alert if isinstance(alert, int) else alert.alert_id
        async with self._lock:
            return self._alerts.pop(alert_id, None) is not None

    async def remove_for(self, chat_id: int, alert_id: int | None = None) -> int:
        async with self._lock:
            ids = [key for key, value in self._alerts.items()
                   if value.chat_id == chat_id and (alert_id is None or key == alert_id)]
            for key in ids:
                del self._alerts[key]
            return len(ids)

    async def snapshot(self) -> list[Alert]:
        async with self._lock:
            return list(self._alerts.values())


class AlertWorker:
    """Poll active alerts and notify once when market price reaches target."""
    def __init__(self, market: PriceClient, store: AlertStore,
                 send: Callable[[int, str], Awaitable[None]], interval: float = 15.0):
        if interval <= 0:
            raise ValueError("interval must be positive")
        self.market, self.store, self.send, self.interval = market, store, send, interval

    async def check_once(self) -> None:
        for alert in await self.store.snapshot():
            try:
                ticker = await self.market.get_price(alert.symbol)
                if ticker.price >= alert.target_price:
                    # Remove before sending, preventing duplicate notifications on retries.
                    if await self.store.remove(alert):
                        await self.send(
                            alert.chat_id,
                            f"🔔 {ticker.symbol} reached {ticker.price:g} "
                            f"(target {alert.target_price:g})",
                        )
            except Exception:
                logger.exception("Alert check failed for %s (alert %s)", alert.symbol, alert.alert_id)

    async def run(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            await self.check_once()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass
