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

SPEC = json.loads((ROOT / "catalog" / "ads" / "spotify.json").read_text(encoding="utf-8"))
A = "https://api-partner.spotify.com/ads/v3"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "spcid", "client_secret": "spsecret", "refresh_token": "sprefresh1", "business_id": "biz1", "ad_account_id": "acc1"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://accounts.spotify.com/api/token").mock(return_value=httpx.Response(200, json={"access_token": "SPTOKEN1", "token_type": "Bearer", "expires_in": 3600}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume"]


@pytest.mark.asyncio
@respx.mock
async def test_basic_refresh_and_campaign_filter():
    token = _token()
    route = respx.get(f"{A}/ad_accounts/acc1/campaigns").mock(return_value=httpx.Response(200, json={"paging": {"total_results": 1}, "campaigns": [{"id": "c1", "name": "Summer Beats", "status": "ACTIVE"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "acc1", "status": "ACTIVE", "limit": 10})
    treq = token.calls[0].request
    assert treq.headers["Authorization"].startswith("Basic ") and _form(treq) == {"grant_type": "refresh_token", "refresh_token": "sprefresh1"}
    assert dict(route.calls[0].request.url.params) == {"statuses": "ACTIVE", "limit": "10", "offset": "0"}
    assert res.structured_content["campaigns"][0]["name"] == "Summer Beats" and res.structured_content["total"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_aggregate_report_repeats_fields_and_keeps_stats_list():
    _token()
    route = respx.get(f"{A}/ad_accounts/acc1/aggregate_reports").mock(return_value=httpx.Response(200, json={"rows": [
        {"entity_type": "CAMPAIGN", "entity_id": "c1", "entity_name": "Summer Beats", "stats": [{"field_type": "IMPRESSIONS", "field_value": 1920}, {"field_type": "SPEND", "field_value": 17.48}]}]}))
    res = await _server().call_tool("get_report", {"account_id": "acc1", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    url = route.calls[0].request.url
    assert url.params.get_list("fields") == ["IMPRESSIONS", "CLICKS", "SPEND"]
    assert (url.params["report_start"], url.params["report_end"], url.params["entity_type"]) == ("2026-09-01T00:00:00Z", "2026-09-07T00:00:00Z", "CAMPAIGN")
    r = res.structured_content["rows"][0]
    assert r["campaign_id"] == "c1" and r["stats"][1] == {"field_type": "SPEND", "field_value": 17.48}


@pytest.mark.asyncio
@respx.mock
async def test_pause_patch_and_server_error():
    _token()
    route = respx.patch(f"{A}/ad_accounts/acc1/campaigns/c1").mock(side_effect=[httpx.Response(200, json={"id": "c1", "status": "PAUSED"}), httpx.Response(500, json={"error": "boom"})])
    res = await _server().call_tool("pause_resume", {"campaign_id": "c1", "action": "pause"})
    assert json.loads(route.calls[0].request.content) == {"status": "PAUSED"} and res.structured_content["status"] == "PAUSED"
    bad = await _server().call_tool("pause_resume", {"campaign_id": "c1", "action": "resume"})
    assert bad.structured_content["error"] == "upstream_error" and "SPTOKEN1" not in json.dumps(bad.structured_content)
