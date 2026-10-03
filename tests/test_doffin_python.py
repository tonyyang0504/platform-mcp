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

SPEC = json.loads((ROOT / "catalog" / "deals" / "doffin.json").read_text(encoding="utf-8"))
URL = "https://api.doffin.no/public/v2/search"
KEY = "doffin-sub-key-0123456789abcdef"

# PublicNoticeHitDto per the developer-portal schema (opened 2026-09-25)
HIT = {
    "id": "2026-105123", "buyer": [{"id": "b1", "organizationId": "974760673", "name": "Statens vegvesen"}],
    "heading": "Vedlikehold av riksvei", "description": "Drift og vedlikehold …", "locationId": ["NO0301"],
    "estimatedValue": {"currencyCode": "NOK", "amount": 25000000}, "type": "COMPETITION", "status": "ACTIVE",
    "issueDate": "2026-09-20", "publicationDate": "2026-09-20", "deadline": "2026-10-30T12:00:00Z", "cpvCodes": ["45233141"],
}


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds if creds is not None else {"subscription_key": KEY}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search_postings"]
    assert "download" in SPEC["adapter"]["not_offered"]["get_posting"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_key_header_and_documented_params():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"numHitsTotal": 57, "numHitsAccessible": 57, "hits": [HIT]}))
    res = await _server().call_tool("search_postings", {"query": "riksvei", "category": "45233141", "min_budget": 1000000, "page": 2, "limit": 10})
    assert res.is_error is False
    req = route.calls.last.request
    assert req.headers["Ocp-Apim-Subscription-Key"] == KEY and "subscription-key" not in req.url.params
    assert dict(req.url.params) == {"searchString": "riksvei", "cpvCode": "45233141", "estimatedValueFrom": "1000000", "page": "2", "numHitsPerPage": "10", "status": "ACTIVE"}
    p = res.structured_content["postings"][0]
    assert p["id"] == "2026-105123" and p["title"] == "Vedlikehold av riksvei" and p["buyer"] == "Statens vegvesen"
    assert p["budget_max"] == 25000000 and p["currency"] == "NOK" and p["skills"] == ["45233141"] and p["deadline"] == "2026-10-30T12:00:00Z"
    assert res.structured_content["total"] == 57


@pytest.mark.asyncio
@respx.mock
async def test_fractional_min_budget_is_invalid_input():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"numHitsTotal": 0, "hits": []}))
    res = await _server().call_tool("search_postings", {"min_budget": 10.5})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and not route.called


@pytest.mark.asyncio
@respx.mock
async def test_401_is_auth_error_without_the_key():
    respx.get(URL).mock(return_value=httpx.Response(401, json={"statusCode": 401, "message": f"Access denied due to invalid subscription key {KEY}."}))
    res = await _server().call_tool("search_postings", {"query": "vei"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert KEY not in json.dumps(res.structured_content)
