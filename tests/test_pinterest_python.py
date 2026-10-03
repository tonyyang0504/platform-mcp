import base64
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


SPEC = json.loads((ROOT / "catalog" / "ads" / "pinterest.json").read_text(encoding="utf-8"))
P = "https://api.pinterest.com/v5"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "1480000", "client_secret": "pinsecret", "refresh_token": "pinr.abc", "ad_account_id": "549755885175"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_ads_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_uses_basic_client_auth_then_bearer():
    token = respx.post(f"{P}/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "pina_AT", "expires_in": 2592000, "refresh_token": "pinr.new", "token_type": "bearer", "response_type": "refresh_token"}))
    route = respx.get(f"{P}/ad_accounts/549755885175/campaigns").mock(return_value=httpx.Response(200, json={"items": [
        {"id": "626735565838", "ad_account_id": "549755885175", "name": "ACME Tools", "status": "ACTIVE", "daily_spend_cap": 1432744744, "start_time": 1580865126}], "bookmark": None}))
    res = await _server().call_tool("list_campaigns", {"account_id": "549755885175", "status": "PAUSED", "limit": 50})
    assert res.is_error is False
    treq = token.calls[0].request
    assert treq.headers["Authorization"] == "Basic " + base64.b64encode(b"1480000:pinsecret").decode()
    assert _form(treq) == {"grant_type": "refresh_token", "refresh_token": "pinr.abc"}
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer pina_AT" and req.url.params["entity_statuses"] == "PAUSED" and req.url.params["page_size"] == "50"
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"]) == ("626735565838", "ACME Tools", "ACTIVE") and c["raw"]["daily_spend_cap"] == 1432744744


@pytest.mark.asyncio
@respx.mock
async def test_get_report_maps_the_top_level_array_of_daily_rows():
    respx.post(f"{P}/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "pina_AT", "expires_in": 3600}))
    route = respx.get(f"{P}/ad_accounts/549755885175/campaigns/analytics").mock(return_value=httpx.Response(200, json=[
        {"CAMPAIGN_ID": "626735565838", "DATE": "2026-09-01", "SPEND_IN_DOLLAR": 12.5, "IMPRESSION_1": 1000, "CLICKTHROUGH_1": 17}]))
    res = await _server().call_tool("get_report", {"account_id": "549755885175", "campaign_id": "626735565838", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    r = res.structured_content["rows"][0]
    assert (r["campaign_id"], r["date"], r["spend"], r["impressions"], r["clicks"]) == ("626735565838", "2026-09-01", 12.5, 1000, 17)
    p = route.calls[0].request.url.params
    assert p["campaign_ids"] == "626735565838" and p["granularity"] == "DAY" and p["columns"].startswith("SPEND_IN_DOLLAR,IMPRESSION_1") and p["start_date"] == "2026-09-01"


@pytest.mark.asyncio
@respx.mock
async def test_refused_refresh_token_is_an_auth_error_without_secrets():
    respx.post(f"{P}/oauth/token").mock(return_value=httpx.Response(401, json={"code": 2, "message": "Authentication failed.", "status": "failure"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "pinsecret" not in json.dumps(res.structured_content) and "pinr.abc" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_and_pause_resume_patch_a_top_level_array_under_the_configured_account():
    respx.post(f"{P}/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "pina_AT", "expires_in": 3600}))
    route = respx.patch(f"{P}/ad_accounts/549755885175/campaigns").mock(side_effect=[
        httpx.Response(200, json={"items": [{"data": {"id": "626735565838", "status": "ACTIVE", "daily_spend_cap": 25000000}, "exceptions": []}]}),
        httpx.Response(200, json={"items": [{"data": {"id": "626735565838", "status": "PAUSED"}, "exceptions": []}]}),
        httpx.Response(200, json={"items": [{"exceptions": [{"code": 2, "message": "Invalid spend cap"}]}]})])
    res = await _server().call_tool("update_budget", {"campaign_id": "626735565838", "daily_budget": 25000000})
    assert res.is_error is False and res.structured_content["status"] == "updated" and res.structured_content["campaign_id"] == "626735565838"
    assert json.loads(route.calls[0].request.content) == [{"id": "626735565838", "daily_spend_cap": 25000000}]
    res = await _server().call_tool("pause_resume", {"campaign_id": "626735565838", "action": "pause"})
    assert res.structured_content["status"] == "PAUSED" and json.loads(route.calls[1].request.content) == [{"id": "626735565838", "status": "PAUSED"}]
    bad = await _server().call_tool("update_budget", {"campaign_id": "626735565838", "daily_budget": 1})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
