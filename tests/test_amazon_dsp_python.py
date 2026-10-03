import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402


def _form(req):
    return {k: v[0] for k, v in parse_qs(req.content.decode()).items()}


async def _names(server):
    return sorted(t.name for t in await server.list_tools())

SPEC = json.loads((ROOT / "catalog" / "ads" / "amazon_dsp.json").read_text(encoding="utf-8"))
A = "https://advertising-api-eu.amazon.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "amzn1.cid", "client_secret": "lwasecret", "refresh_token": "Atzr|refresh", "api_host": "advertising-api-eu.amazon.com", "profile_id": "4001"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["list_accounts", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_dsp_advertisers_paging_and_headers():
    respx.post("https://api.amazon.com/auth/o2/token").mock(return_value=httpx.Response(200, json={"access_token": "Atza|D", "expires_in": 3600}))
    route = respx.get(f"{A}/dsp/advertisers").mock(return_value=httpx.Response(200, json={"totalResults": 1100, "response": [
        {"advertiserId": "4728736040201", "name": "DSP Public API Advertiser", "currency": "EUR", "country": "DE"}]}))
    res = await _server().call_tool("list_accounts", {})
    req = route.calls[0].request
    assert dict(req.url.params) == {"startIndex": "0", "count": "25"}
    assert req.headers["Amazon-Advertising-API-Scope"] == "4001"
    a = res.structured_content["accounts"][0]
    assert (a["id"], a["currency"]) == ("4728736040201", "EUR") and res.structured_content["total"] == 1100


@pytest.mark.asyncio
@respx.mock
async def test_throttled_list_is_rate_limited():
    respx.post("https://api.amazon.com/auth/o2/token").mock(return_value=httpx.Response(200, json={"access_token": "Atza|D", "expires_in": 3600}))
    respx.get(f"{A}/dsp/advertisers").mock(return_value=httpx.Response(429, headers={"Retry-After": "3"}, json={"message": "Too Many Requests"}))
    res = await _server().call_tool("list_accounts", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
