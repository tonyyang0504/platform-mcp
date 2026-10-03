"""CoinPaprika (forge stress test 2026-10): the documented /v1/search answers 301 to /v1/search/ — the runtime follows
same-origin redirects (before: an empty success in Python, data in TypeScript) and refuses cross-origin ones."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "coinpaprika.json").read_text(encoding="utf-8"))
BASE = "https://api.coinpaprika.com/v1"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_search_follows_the_same_origin_redirect():
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(301, headers={"location": "/v1/search/?q=bitcoin&c=currencies&limit=2"}, text="Moved Permanently"))
    route = respx.get(f"{BASE}/search/").mock(return_value=httpx.Response(200, json={"currencies": [{"id": "btc-bitcoin", "name": "Bitcoin", "symbol": "BTC", "type": "coin"}]}))
    r = (await _server().call_tool("search_symbols", {"query": "bitcoin", "limit": 2})).structured_content
    assert r["results"][0]["symbol"] == "btc-bitcoin" and r["results"][0]["name"] == "Bitcoin"
    assert route.calls.last.request.url.params["q"] == "bitcoin"


@pytest.mark.asyncio
@respx.mock
async def test_cross_origin_redirect_is_refused():
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(302, headers={"location": "https://evil.example/collect"}))
    other = respx.get("https://evil.example/collect").mock(return_value=httpx.Response(200, json={}))
    r = await _server().call_tool("search_symbols", {"query": "bitcoin"})
    assert r.is_error and r.structured_content["error"] == "upstream_error" and "evil.example" in r.structured_content["message"]
    assert not other.called


@pytest.mark.asyncio
@respx.mock
async def test_html_body_is_an_error_not_an_empty_result():
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(200, headers={"content-type": "text/html"}, text="<html><body>Just a moment...</body></html>"))
    r = await _server().call_tool("search_symbols", {"query": "bitcoin"})
    assert r.is_error and r.structured_content["error"] == "upstream_error" and "text/html" in r.structured_content["message"]
