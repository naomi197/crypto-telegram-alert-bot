import asyncio
from types import SimpleNamespace

import pytest

from src.alerts import AlertStore, AlertWorker


@pytest.mark.asyncio
async def test_store_scopes_and_cancels_alerts():
    store = AlertStore()
    one = await store.add(10, "BTCUSDT", 70000)
    two = await store.add(10, "ETHUSDT", 4000)
    await store.add(11, "BTCUSDT", 80000)
    assert one.alert_id != two.alert_id
    assert [a.alert_id for a in await store.list_for(10)] == [one.alert_id, two.alert_id]
    assert await store.remove_for(10, one.alert_id) == 1
    assert [a.alert_id for a in await store.list_for(10)] == [two.alert_id]
    assert await store.remove_for(10) == 1
    assert len(await store.snapshot()) == 1


@pytest.mark.asyncio
async def test_worker_notifies_once_when_price_reaches_target():
    store = AlertStore()
    await store.add(42, "BTCUSDT", 100)
    sent = []

    class FakeMarket:
        async def get_price(self, symbol):
            return SimpleNamespace(symbol=symbol, price=100.5)

    async def send(chat_id, text):
        sent.append((chat_id, text))

    worker = AlertWorker(FakeMarket(), store, send)
    await worker.check_once()
    await worker.check_once()
    assert len(sent) == 1
    assert sent[0][0] == 42
    assert "BTCUSDT reached 100.5" in sent[0][1]
    assert await store.snapshot() == []


@pytest.mark.asyncio
async def test_worker_does_not_notify_below_target():
    store = AlertStore()
    await store.add(42, "BTCUSDT", 101)
    sent = []

    class FakeMarket:
        async def get_price(self, symbol):
            return SimpleNamespace(symbol=symbol, price=100)

    async def send(chat_id, text):
        sent.append(text)

    await AlertWorker(FakeMarket(), store, send).check_once()
    assert sent == []
    assert len(await store.snapshot()) == 1
