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

SPEC = json.loads((ROOT / "catalog" / "ads" / "otto_retail_media.json").read_text(encoding="utf-8"))
A = "https://api.otto.market"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "ottocid", "client_secret": "ottosecret"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(f"{A}/v1/token").mock(return_value=httpx.Response(200, json={"access_token": "OTTOJWT", "expires_in": 1800, "token_type": "Bearer", "scope": "advertising-services"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_scope_and_campaign_list():
    token = _token()
    route = respx.get(f"{A}/v1/sponsored-product-ads/campaigns").mock(return_value=httpx.Response(200, json={"campaigns": [
        {"campaignId": "a1b2", "name": "Herbst", "status": "ACTIVE", "startDate": "2026-09-01", "endDate": None, "budget": {"amount": 50, "currency": "EUR"}, "budgetType": "DAILY"}], "_links": {}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "me"})
    assert _form(token.calls[0].request) == {"grant_type": "client_credentials", "scope": "advertising-services", "client_id": "ottocid", "client_secret": "ottosecret"}
    assert route.calls[0].request.url.params["limit"] == "25"
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["currency"], c["status"]) == ("a1b2", 50, "EUR", "ACTIVE")


@pytest.mark.asyncio
@respx.mock
async def test_merge_patch_budget_returns_pending_change_request():
    _token()
    route = respx.patch(f"{A}/v1/sponsored-product-ads/campaigns/a1b2").mock(return_value=httpx.Response(202, json={
        "changeRequest": {"requestId": "3fa8", "requestType": "UPDATE_CAMPAIGN", "status": "PENDING", "lastModifiedAt": "2026-09-25T08:00:00Z"}, "_links": {}}))
    res = await _server().call_tool("update_budget", {"campaign_id": "a1b2", "daily_budget": 75})
    req = route.calls[0].request
    assert req.headers["Content-Type"] == "application/merge-patch+json"
    assert json.loads(req.content) == {"budget": {"amount": 75, "currency": "EUR"}}
    assert res.structured_content["status"] == "PENDING" and res.structured_content["request_id"] == "3fa8"
    bad = await _server().call_tool("update_budget", {"campaign_id": "a1b2", "daily_budget": 75.5})
    assert bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_pending_conflict_is_conflict_and_secret_scrubbed():
    _token()
    respx.patch(f"{A}/v1/sponsored-product-ads/campaigns/a1b2").mock(return_value=httpx.Response(409, json={"errors": [{"message": "A change request for this campaign is already in progress."}]}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "a1b2", "action": "pause"})
    assert res.structured_content["error"] == "conflict" and "ottosecret" not in json.dumps(res.structured_content)
