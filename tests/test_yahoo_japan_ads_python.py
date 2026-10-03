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

SPEC = json.loads((ROOT / "catalog" / "ads" / "yahoo_japan_ads.json").read_text(encoding="utf-8"))
A = "https://ads-search.yahooapis.jp/api/v20"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "yjcid", "client_secret": "yjsecret", "refresh_token": "yjrefresh1", "base_account_id": "1000", "account_id": "2000"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://biz-oauth.yahoo.co.jp/oauth/v1/token").mock(return_value=httpx.Response(200, json={"access_token": "YJTOKEN1", "expires_in": 3600, "token_type": "Bearer"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_campaign_get_with_base_account_header():
    token = _token()
    route = respx.post(f"{A}/CampaignService/get").mock(return_value=httpx.Response(200, json={"rid": "r1", "rval": {"totalNumEntries": 1, "values": [
        {"operationSucceeded": True, "campaign": {"campaignId": 11, "campaignName": "Brand", "userStatus": "ACTIVE", "budget": {"amount": 5000}}}]}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "2000", "status": "ACTIVE"})
    assert _form(token.calls[0].request)["refresh_token"] == "yjrefresh1"
    req = route.calls[0].request
    assert req.headers["x-z-base-account-id"] == "1000" and req.headers["Authorization"] == "Bearer YJTOKEN1"
    assert json.loads(req.content) == {"accountId": 2000, "userStatuses": ["ACTIVE"], "numberResults": 25}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["currency"]) == ("11", 5000, "JPY") and res.structured_content["total"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_set_budget_and_status_bodies():
    _token()
    route = respx.post(f"{A}/CampaignService/set").mock(return_value=httpx.Response(200, json={"rid": "r2", "rval": {"values": [{"operationSucceeded": True, "campaign": {"campaignId": 11, "userStatus": "PAUSED"}}]}}))
    r1 = await _server().call_tool("update_budget", {"campaign_id": "11", "daily_budget": 8000})
    r2 = await _server().call_tool("pause_resume", {"campaign_id": "11", "action": "pause"})
    assert json.loads(route.calls[0].request.content) == {"accountId": 2000, "operand": [{"campaignId": 11, "budget": {"amount": 8000}}]}
    assert json.loads(route.calls[1].request.content) == {"accountId": 2000, "operand": [{"campaignId": 11, "userStatus": "PAUSED"}]}
    assert r1.structured_content["operation_succeeded"] is True and r2.structured_content["status"] == "PAUSED"


@pytest.mark.asyncio
@respx.mock
async def test_permission_denied_is_auth_error_without_leak():
    _token()
    respx.post(f"{A}/BaseAccountService/get").mock(return_value=httpx.Response(403, json={"errors": [{"code": "0098", "message": "Permission denied. YJTOKEN1"}]}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "YJTOKEN1" not in json.dumps(res.structured_content)
