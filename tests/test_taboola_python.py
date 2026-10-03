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

SPEC = json.loads((ROOT / "catalog" / "ads" / "taboola.json").read_text(encoding="utf-8"))
A = "https://backstage.taboola.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "tbcid", "client_secret": "tbsecret", "account_id": "demo-advertiser"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(f"{A}/backstage/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "CZ0OAAAAtoken", "token_type": "bearer", "expires_in": 43200}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_campaigns_trailing_slash_and_daily_cap():
    token = _token()
    route = respx.get(f"{A}/backstage/api/1.0/demo-advertiser/campaigns/").mock(return_value=httpx.Response(200, json={"results": [
        {"id": "5750752", "name": "Demo Campaign 1", "status": "RUNNING", "is_active": True, "daily_cap": 100, "start_date": "2026-09-01", "end_date": None}], "metadata": {}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "demo-advertiser"})
    assert _form(token.calls[0].request) == {"grant_type": "client_credentials", "client_id": "tbcid", "client_secret": "tbsecret"}
    assert route.calls[0].request.url.params["fetch_level"] == "RAP"
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["status"]) == ("5750752", 100, "RUNNING")


@pytest.mark.asyncio
@respx.mock
async def test_budget_update_and_campaign_day_report():
    _token()
    upd = respx.post(f"{A}/backstage/api/1.0/demo-advertiser/campaigns/5750752").mock(return_value=httpx.Response(200, json={"id": "5750752", "daily_cap": 150}))
    res = await _server().call_tool("update_budget", {"campaign_id": "5750752", "daily_budget": 150})
    assert json.loads(upd.calls[0].request.content) == {"daily_cap": 150}
    assert res.structured_content["status"] == "updated" and res.structured_content["daily_cap"] == 150
    rep = respx.get(f"{A}/backstage/api/1.0/demo-advertiser/reports/campaign-summary/dimensions/campaign_day_breakdown").mock(return_value=httpx.Response(200, json={"results": [
        {"date": "2026-09-01 00:00:00.0", "campaign": "5750752", "campaign_name": "Demo", "impressions": 154, "clicks": 3, "spent": 1.2, "currency": "USD"}], "recordCount": 1}))
    r = await _server().call_tool("get_report", {"account_id": "demo-advertiser", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert dict(rep.calls[0].request.url.params) == {"start_date": "2026-09-01", "end_date": "2026-09-07"}
    assert r.structured_content["rows"][0]["spend"] == 1.2


@pytest.mark.asyncio
@respx.mock
async def test_bad_client_credentials_is_auth_error_without_leak():
    respx.post(f"{A}/backstage/oauth/token").mock(return_value=httpx.Response(400, text="<BadClientCredentialsException><error>invalid_client</error><error_description>tbsecret rejected</error_description></BadClientCredentialsException>"))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "tbsecret" not in json.dumps(res.structured_content)
