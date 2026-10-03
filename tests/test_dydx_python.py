"""dYdX v4 indexer (forge stress test 2026-10): markets keyed by ticker (items_are_values, markets.*)."""
import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "trading" / "dydx.json").read_text(encoding="utf-8"))
BASE = "https://indexer.dydx.trade/v4"
MKTS = {"markets": {"ETH-USD": {"ticker": "ETH-USD", "oraclePrice": "2707.45", "volume24H": "45248782.5", "marketType": "CROSS"},
                    "BTC-USD": {"ticker": "BTC-USD", "oraclePrice": "83951.4565", "volume24H": "5587345.2", "marketType": "CROSS"}}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_markets_keyed_by_ticker():
    respx.get(f"{BASE}/perpetualMarkets").mock(side_effect=lambda req: httpx.Response(200, json=MKTS if "ticker" not in req.url.params else
                                                                                      ({"markets": {k: v for k, v in MKTS["markets"].items() if k == req.url.params["ticker"]}})))
    m = (await _server().call_tool("list_markets", {})).structured_content
    assert [x["symbol"] for x in m["markets"]] == ["BTC-USD", "ETH-USD"]
    t = (await _server().call_tool("get_ticker", {"symbol": "BTC-USD"})).structured_content
    assert (t["symbol"], t["last"], t["volume"]) == ("BTC-USD", 83951.4565, 5587345.2)
    r = await _server().call_tool("get_ticker", {"symbol": "ZZZ-USD"})
    assert r.is_error and r.structured_content["error"] == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_candles_and_bad_ticker():
    route = respx.get(f"{BASE}/candles/perpetualMarkets/BTC-USD").mock(return_value=httpx.Response(200, json={"candles": [
        {"startedAt": "2026-10-01T11:00:00.000Z", "open": "83979", "high": "83979", "low": "83740", "close": "83910", "baseTokenVolume": "0.1581"}]}))
    c = (await _server().call_tool("get_candles", {"symbol": "BTC-USD", "interval": "1h", "limit": 1})).structured_content["candles"]
    assert c[0]["close"] == 83910 and route.calls.last.request.url.params["resolution"] == "1HOUR"
    respx.get(f"{BASE}/candles/perpetualMarkets/NOPE").mock(return_value=httpx.Response(400, json={"errors": [{"msg": "ticker must be a valid ticker (BTC-USD, etc)"}]}))
    r = await _server().call_tool("get_candles", {"symbol": "NOPE", "interval": "1h"})
    assert r.is_error and r.structured_content["error"] == "invalid_input"
