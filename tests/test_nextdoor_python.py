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

# ads/nextdoor (Nextdoor Ads API v3); the social Publish API is tested in test_nextdoor_social_python.py
SPEC = json.loads((ROOT / "catalog" / "ads" / "nextdoor.json").read_text(encoding="utf-8"))
B = "https://ads.nextdoor.com/api/v3"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"api_token": "nam-secret-token", "advertiser_id": "adv1"}, 50, "test"))


@pytest.mark.asyncio
async def test_tools_follow_the_ads_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["list_accounts", "list_campaigns", "me", "pause_resume"]
    assert next(t for t in tools if t.name == "pause_resume").annotations.read_only_hint is False


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts_reads_advertisers_with_access():
    route = respx.get(f"{B}/me").mock(return_value=httpx.Response(200, json={"profile": {"id": "p1", "name": "Shop"}, "user": {"id": "u1", "advertisers_with_access": [{"id": "adv1", "role": "ADMIN"}]}}))
    res = await _server().call_tool("list_accounts", {})
    assert res.is_error is False and res.structured_content["accounts"][0]["id"] == "adv1" and res.structured_content["accounts"][0]["role"] == "ADMIN"
    assert route.calls.last.request.headers["Authorization"] == "Bearer nam-secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_maps_data_records():
    route = respx.get(f"{B}/advertisers/adv1/campaigns").mock(return_value=httpx.Response(200, json={"campaigns": [{"data": {"id": "c1", "name": "Fall", "status": "ACTIVE", "start_time": "2026-09-01T00:00:00Z", "end_time": None}}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "adv1", "limit": 10})
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "c1" and c["name"] == "Fall" and c["status"] == "ACTIVE"
    assert route.calls.last.request.url.params["pageSize"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_puts_user_status_and_errors_hide_the_token():
    route = respx.put(f"{B}/advertisers/adv1/campaigns/c1/status").mock(return_value=httpx.Response(200, json={"id": "c1", "status": "PAUSED", "user_status": "PAUSED"}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "c1", "action": "pause"})
    assert res.is_error is False and res.structured_content["user_status"] == "PAUSED"
    assert json.loads(route.calls.last.request.content) == {"user_status": "PAUSED"}
    respx.get(f"{B}/me").mock(return_value=httpx.Response(401, json={"error": "bad token nam-secret-token"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "nam-secret-token" not in json.dumps(res.structured_content)
