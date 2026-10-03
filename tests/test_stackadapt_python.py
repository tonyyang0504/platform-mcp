import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "stackadapt.json").read_text(encoding="utf-8"))
B = "https://api.stackadapt.com/service/v2"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"rest_api_key": "sa-rest-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "list_campaigns"}


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_pages_with_x_authorization():
    route = respx.get(f"{B}/campaigns").mock(return_value=httpx.Response(200, json={"object": "campaign", "page": 2, "total_campaigns": 31, "data": [
        {"id": 55, "advertiser_id": 12, "line_item_id": 22, "name": "API Test Campaign", "budget": 10000.0, "state": "paused", "start_date": "2026-09-01", "end_date": "2026-09-30"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "12", "page": 2})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["X-Authorization"] == "sa-rest-secret"
    assert parse_qs(urlparse(str(req.url)).query) == {"page": ["2"]}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget"], c["advertiser_id"], res.structured_content["total"]) == ("55", "paused", 10000.0, "12", 31)


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts():
    respx.get(f"{B}/advertisers").mock(return_value=httpx.Response(200, json={"object": "Advertiser", "page": 1, "total_advertisers": 1, "data": [{"id": 12, "name": "Acme"}]}))
    res = await _server().call_tool("list_accounts", {})
    assert res.structured_content["accounts"][0] | {"raw": None} == {"id": "12", "name": "Acme", "raw": None}


@pytest.mark.asyncio
@respx.mock
async def test_refused_key_does_not_leak():
    respx.get(f"{B}/advertisers").mock(return_value=httpx.Response(401, json={"message": "invalid key sa-rest-secret"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "sa-rest-secret" not in json.dumps(res.structured_content)
