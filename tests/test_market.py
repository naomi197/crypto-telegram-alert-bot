import pytest

from src.market import AsyncMarketClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    async def json(self):
        return self.payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.request = None

    def get(self, *args, **kwargs):
        self.request = (args, kwargs)
        return FakeResponse(self.payload)


@pytest.mark.asyncio
async def test_get_price_parses_public_ticker():
    session = FakeSession({"symbol": "BTCUSDT", "price": "65000.12"})
    async with AsyncMarketClient("https://example.test", session=session) as client:
        ticker = await client.get_price("btc/usdt")
    assert ticker.symbol == "BTCUSDT"
    assert ticker.price == pytest.approx(65000.12)
    assert session.request[1]["params"] == {"symbol": "BTCUSDT"}


def test_normalize_symbol():
    assert AsyncMarketClient.normalize_symbol(" eth/usdt ") == "ETHUSDT"
    with pytest.raises(ValueError):
        AsyncMarketClient.normalize_symbol("BTC-USDT")
    with pytest.raises(ValueError):
        AsyncMarketClient.normalize_symbol("")


@pytest.mark.asyncio
async def test_invalid_ticker_response_is_rejected():
    async with AsyncMarketClient("https://example.test", session=FakeSession(
        {"symbol": "BTCUSDT", "price": "nan"}
    )) as client:
        with pytest.raises(ValueError, match="invalid ticker"):
            await client.get_price("BTCUSDT")
