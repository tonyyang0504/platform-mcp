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

SPEC = json.loads((ROOT / "catalog" / "ads" / "amazon_fire_tv_ads.json").read_text(encoding="utf-8"))
A = "https://advertising-api.amazon.com"
MT = "application/vnd.stCampaign.v1+json"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "amzn1.cid", "client_secret": "lwasecret", "refresh_token": "Atzr|refresh", "api_host": "advertising-api.amazon.com", "profile_id": "3001"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://api.amazon.com/auth/o2/token").mock(return_value=httpx.Response(200, json={"access_token": "Atza|X", "expires_in": 3600}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_uses_st_media_type_and_scope_headers():
    _token()
    route = respx.post(f"{A}/st/campaigns/list").mock(return_value=httpx.Response(200, json={"campaigns": [
        {"campaignId": "310305299990960", "name": "Fire TV launch", "state": "ENABLED", "budgetSettings": {"budget": {"budgetValue": {"amount": 250.0, "budgetCurrencyCode": "USD"}, "recurrenceType": "DAILY"}}, "startDate": "20260901"}], "totalCount": 1}))
    res = await _server().call_tool("list_campaigns", {"account_id": "3001", "status": "ENABLED"})
    req = route.calls[0].request
    assert req.headers["Content-Type"] == MT and req.headers["Accept"] == MT
    assert req.headers["Amazon-Advertising-API-Scope"] == "3001" and req.headers["Amazon-Advertising-API-ClientId"] == "amzn1.cid"
    assert req.headers["Authorization"] == "Bearer Atza|X"
    assert json.loads(req.content) == {"maxResults": 25, "stateFilter": {"include": ["ENABLED"]}}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["currency"], c["status"]) == ("310305299990960", 250.0, "USD", "ENABLED")
    assert res.structured_content["total"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_body_and_rejection():
    _token()
    route = respx.put(f"{A}/st/campaigns").mock(side_effect=[
        httpx.Response(207, json={"campaigns": {"success": [{"campaignId": "31", "index": 0}], "error": []}}),
        httpx.Response(207, json={"campaigns": {"success": [], "error": [{"index": 0, "errors": [{"errorType": "budget"}]}]}})])
    res = await _server().call_tool("update_budget", {"campaign_id": "31", "daily_budget": 120.5, "currency": "USD"})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert json.loads(route.calls[0].request.content) == {"campaigns": [{"campaignId": "31", "budgetSettings": {"budget": {"budgetValue": {"amount": 120.5, "budgetCurrencyCode": "USD"}, "recurrenceType": "DAILY"}}}]}
    bad = await _server().call_tool("update_budget", {"campaign_id": "31", "daily_budget": 0})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_pause_maps_state_and_refused_refresh_is_scrubbed():
    _token()
    route = respx.put(f"{A}/st/campaigns").mock(return_value=httpx.Response(207, json={"campaigns": {"success": [{"campaignId": "31", "index": 0, "campaign": {"state": "PAUSED"}}]}}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "31", "action": "pause"})
    assert json.loads(route.calls[0].request.content) == {"campaigns": [{"campaignId": "31", "state": "PAUSED"}]}
    assert res.structured_content["status"] == "PAUSED"
    respx.post("https://api.amazon.com/auth/o2/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "Atzr|refresh lwasecret"}))
    fresh = _server()
    bad = await fresh.call_tool("me", {})
    assert bad.structured_content["error"] == "auth_error"
    assert "Atzr|refresh" not in json.dumps(bad.structured_content) and "lwasecret" not in json.dumps(bad.structured_content)
