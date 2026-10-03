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

SPEC = json.loads((ROOT / "catalog" / "ads" / "dv360.json").read_text(encoding="utf-8"))
A = "https://displayvideo.googleapis.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "gcid", "client_secret": "gsecret", "refresh_token": "1//dvrefresh", "partner_id": "123", "advertiser_id": "456"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(200, json={"access_token": "ya29.DV", "expires_in": 3599}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["list_accounts", "list_campaigns", "me", "pause_resume"]


@pytest.mark.asyncio
@respx.mock
async def test_advertisers_use_partner_config_and_campaign_status_filter():
    _token()
    adv = respx.get(f"{A}/v4/advertisers").mock(return_value=httpx.Response(200, json={"advertisers": [{"advertiserId": "456", "displayName": "Brand", "generalConfig": {"currencyCode": "EUR"}}]}))
    res = await _server().call_tool("list_accounts", {})
    assert dict(adv.calls[0].request.url.params) == {"partnerId": "123", "pageSize": "25"}
    assert res.structured_content["accounts"][0]["currency"] == "EUR"
    camp = respx.get(f"{A}/v4/advertisers/456/campaigns").mock(return_value=httpx.Response(200, json={"campaigns": [{"campaignId": "9", "displayName": "Q4", "entityStatus": "ENTITY_STATUS_PAUSED"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "456", "status": "paused"})
    assert camp.calls[0].request.url.params["filter"] == 'entityStatus="ENTITY_STATUS_PAUSED"'
    assert res.structured_content["campaigns"][0]["status"] == "ENTITY_STATUS_PAUSED"
    bad = await _server().call_tool("list_campaigns", {"account_id": "456", "status": "x\") OR (1"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_pause_patches_entity_status_with_update_mask():
    _token()
    route = respx.patch(f"{A}/v4/advertisers/456/campaigns/9").mock(return_value=httpx.Response(200, json={"campaignId": "9", "entityStatus": "ENTITY_STATUS_PAUSED"}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "9", "action": "pause"})
    assert route.calls[0].request.url.params["updateMask"] == "entityStatus"
    assert json.loads(route.calls[0].request.content) == {"entityStatus": "ENTITY_STATUS_PAUSED"}
    assert res.structured_content == {"campaign_id": "9", "status": "ENTITY_STATUS_PAUSED", "raw": {"campaignId": "9", "entityStatus": "ENTITY_STATUS_PAUSED"}}


@pytest.mark.asyncio
@respx.mock
async def test_forbidden_is_auth_error_without_token_leak():
    _token()
    respx.get(f"{A}/v4/partners").mock(return_value=httpx.Response(403, json={"error": {"message": "caller ya29.DV lacks access"}}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "ya29.DV" not in json.dumps(res.structured_content)
