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

SPEC = json.loads((ROOT / "catalog" / "ads" / "doordash_ads.json").read_text(encoding="utf-8"))
BASE = "https://openapi.doordash.com/ads/api/v1/sp"
CREDS = {"api_key": "DD-ADS-KEY-secret", "campaign_type": "sp"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_bearer_and_offset_paging():
    route = respx.get(url__startswith=f"{BASE}/campaigns").mock(return_value=httpx.Response(200, json={"campaigns": [
        {"campaignId": "c-1", "name": "Summer", "status": "ACTIVE", "budget": {"daily": {"unitAmount": 5000, "currency": "USD"}},
         "startDate": "2025-11-01 00:00:00", "endDate": "2025-12-01 00:00:00"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "adv-1", "page": 3, "limit": 20})
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "c-1" and c["status"] == "ACTIVE" and c["currency"] == "USD" and c["start"] == "2025-11-01 00:00:00"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer DD-ADS-KEY-secret"
    assert req.url.params["startIndex"] == "40" and req.url.params["count"] == "20"


@pytest.mark.asyncio
@respx.mock
async def test_budget_in_cents_and_pause():
    route = respx.put(f"{BASE}/campaigns").mock(return_value=httpx.Response(200, json={"campaignId": "c-1", "name": "Summer", "status": "PAUSED"}))
    out = (await _server().call_tool("update_budget", {"campaign_id": "c-1", "daily_budget": 25.5})).structured_content
    assert out["status"] == "updated"
    assert json.loads(route.calls[0].request.content) == {"campaignId": "c-1", "budget": {"daily": {"unitAmount": 2550}}}
    assert (await _server().call_tool("pause_resume", {"campaign_id": "c-1", "action": "pause"})).is_error is False
    assert json.loads(route.calls[1].request.content) == {"campaignId": "c-1", "status": "PAUSED"}


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_is_auth_error_and_probe():
    respx.get(url__startswith=f"{BASE}/campaigns").mock(return_value=httpx.Response(401, json={"message": "Unauthorized"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "DD-ADS-KEY-secret" not in res.content[0].text
