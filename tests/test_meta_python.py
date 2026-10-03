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

SPEC = json.loads((ROOT / "catalog" / "ads" / "meta.json").read_text(encoding="utf-8"))
G = "https://graph.facebook.com/v26.0"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "EAAGtok"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_ads_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]
    ub = next(t for t in tools if t.name == "update_budget")
    assert ub.annotations.read_only_hint is False and ub.meta["platform_mcp/docs"].endswith("/reference/ad-campaign-group/")


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts_sends_the_bearer_and_maps_act_ids():
    route = respx.get(f"{G}/me/adaccounts").mock(return_value=httpx.Response(200, json={
        "data": [{"id": "act_1010", "account_id": "1010", "name": "Shop", "currency": "EUR", "account_status": 1, "timezone_name": "Europe/Dublin"}],
        "paging": {"cursors": {"before": "a", "after": "b"}}}))
    res = await _server().call_tool("list_accounts", {})
    assert res.is_error is False
    assert res.structured_content["accounts"][0] == {"id": "act_1010", "name": "Shop", "currency": "EUR", "raw": {"id": "act_1010", "account_id": "1010", "name": "Shop", "currency": "EUR", "account_status": 1, "timezone_name": "Europe/Dublin"}}
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer EAAGtok"
    assert req.url.params["fields"].startswith("id,account_id,name,currency") and req.url.params["limit"] == "100"


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_under_the_act_path_with_the_total_count_summary():
    route = respx.get(f"{G}/act_1010/campaigns").mock(return_value=httpx.Response(200, json={
        "data": [{"id": "120200", "name": "Spring", "status": "PAUSED", "effective_status": "PAUSED", "daily_budget": "5000", "start_time": "2026-03-01T00:00:00+0000"}],
        "paging": {"cursors": {"before": "a", "after": "b"}}, "summary": {"total_count": 1}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "act_1010", "limit": 10})
    assert res.is_error is False
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "120200" and c["status"] == "PAUSED" and c["start"] == "2026-03-01T00:00:00+0000" and res.structured_content["total"] == 1
    assert route.calls[0].request.url.params["summary"] == "total_count" and route.calls[0].request.url.params["limit"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_posts_an_integer_minor_unit_amount():
    route = respx.post(f"{G}/120200").mock(return_value=httpx.Response(200, json={"success": True}))
    res = await _server().call_tool("update_budget", {"campaign_id": "120200", "daily_budget": 5000})
    assert res.is_error is False and res.structured_content["status"] == "updated" and res.structured_content["raw"] == {"success": True}
    assert json.loads(route.calls[0].request.content) == {"daily_budget": 5000}
    bad = await _server().call_tool("update_budget", {"campaign_id": "120200", "daily_budget": "fifty"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"  # int: coercion


@pytest.mark.asyncio
@respx.mock
async def test_graph_error_is_upstream_error_and_does_not_echo_the_token():
    respx.post(f"{G}/120200").mock(return_value=httpx.Response(400, json={"error": {"message": "(#100) Budget too low", "type": "OAuthException", "code": 100}}))
    res = await _server().call_tool("update_budget", {"campaign_id": "120200", "daily_budget": 1})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error" and "Budget too low" in res.structured_content["message"]
    assert "EAAGtok" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_maps_the_enum_to_the_campaign_status():
    route = respx.post(f"{G}/120200").mock(return_value=httpx.Response(200, json={"success": True}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "120200", "action": "pause"})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    await _server().call_tool("pause_resume", {"campaign_id": "120200", "action": "resume"})
    assert [json.loads(c.request.content) for c in route.calls] == [{"status": "PAUSED"}, {"status": "ACTIVE"}]
