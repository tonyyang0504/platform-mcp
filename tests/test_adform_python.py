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

SPEC = json.loads((ROOT / "catalog" / "ads" / "adform.json").read_text(encoding="utf-8"))
A = "https://api.adform.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "adf-cid", "client_secret": "adfsecret"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://id.adform.com/sts/connect/token").mock(return_value=httpx.Response(200, json={"access_token": "ADF", "expires_in": 3600, "token_type": "Bearer"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["list_accounts", "list_campaigns", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_client_credentials_with_scopes_and_campaign_filter():
    token = _token()
    route = respx.get(f"{A}/v1/buyer/campaigns").mock(return_value=httpx.Response(200, json=[
        {"id": 77777, "name": "Campaign 77777", "budget": 1500.5, "startDate": "2026-01-01T00:00:00+00:00", "endDate": "2026-12-31T00:00:00+00:00", "status": "Active", "currency": "DKK", "advertiserId": 33333}]))
    res = await _server().call_tool("list_campaigns", {"account_id": "33333", "status": "Inactive", "page": 2, "limit": 10})
    assert res.is_error is False
    form = _form(token.calls[0].request)
    assert form["grant_type"] == "client_credentials" and form["client_id"] == "adf-cid" and form["client_secret"] == "adfsecret"
    assert form["scope"] == "https://api.adform.com/scope/buyer.advertisers.readonly https://api.adform.com/scope/buyer.campaigns.api.readonly"
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer ADF"
    assert dict(req.url.params) == {"advertisers": "33333", "status": "Inactive", "offset": "10", "limit": "10"}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"], c["budget"], c["currency"]) == ("77777", "Campaign 77777", "Active", 1500.5, "DKK")


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts_reads_the_top_level_array():
    _token()
    respx.get(f"{A}/v1/buyer/advertisers").mock(return_value=httpx.Response(200, json=[{"id": 1, "name": "Microsoft", "timeZone": "Europe/Berlin", "status": "Active"}]))
    res = await _server().call_tool("list_accounts", {})
    assert res.structured_content["accounts"][0]["id"] == "1" and res.structured_content["accounts"][0]["name"] == "Microsoft"


@pytest.mark.asyncio
@respx.mock
async def test_refused_client_does_not_leak_the_secret():
    respx.post("https://id.adform.com/sts/connect/token").mock(return_value=httpx.Response(400, json={"error": "invalid_client", "echo": "adfsecret"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "adfsecret" not in json.dumps(res.structured_content)
