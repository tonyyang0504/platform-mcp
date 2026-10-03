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

SPEC = json.loads((ROOT / "catalog" / "deals" / "topcoder.json").read_text(encoding="utf-8"))

# https://api.topcoder.com/v6/challenges?status=Active&page=1&perPage=1 (opened 2026-09-24): a bare array, totals in X-Total headers
CHALLENGE = {
    "id": "5f4a1c2e-1111-4a5b-9c1d-000000000001", "name": "Point-cloud factory layout", "description": "Creating a digital factory layout from a point-cloud scan...",
    "status": "Active", "track": "Development", "type": "Challenge", "tags": ["Python", "Computer Vision"],
    "prizeSets": [{"type": "placement", "prizes": [{"type": "USD", "value": 1500}, {"type": "USD", "value": 500}]}],
    "phases": [{"name": "Registration", "isOpen": True}], "startDate": "2026-09-20T13:00:00.000Z", "endDate": "2026-10-05T13:00:00.000Z",
    "registrationEndDate": "2026-10-04T13:00:00.000Z", "submissionEndDate": "2026-10-05T13:00:00.000Z", "numOfRegistrants": 42, "numOfSubmissions": 3, "projectId": 12345,
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_search_and_details_are_the_only_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    assert "submit_bid" in SPEC["adapter"]["not_offered"]


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_active_challenges_and_first_prize():
    respx.get("https://api.topcoder.com/v6/challenges").mock(return_value=httpx.Response(200, json=[CHALLENGE], headers={"X-Total": "1", "X-Total-Pages": "1"}))
    res = await _server().call_tool("search_postings", {"page": 1, "limit": 10})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "5f4a1c2e-1111-4a5b-9c1d-000000000001" and p["title"] == "Point-cloud factory layout" and p["skills"] == ["Python", "Computer Vision"]
    assert p["budget_max"] == 1500 and p["currency"] == "USD" and p["deadline"] == "2026-10-05T13:00:00.000Z" and p["posted_at"] == "2026-09-20T13:00:00.000Z"
    assert sc["total"] is None and sc["next_page"] is None
    q = respx.calls.last.request.url.params
    assert q["status"] == "Active" and q["page"] == "1" and q["perPage"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_fetches_one_challenge():
    respx.get("https://api.topcoder.com/v6/challenges/5f4a1c2e-1111-4a5b-9c1d-000000000001").mock(return_value=httpx.Response(200, json=CHALLENGE))
    res = await _server().call_tool("get_posting", {"id": "5f4a1c2e-1111-4a5b-9c1d-000000000001"})
    assert res.is_error is False and res.structured_content["title"] == "Point-cloud factory layout" and res.structured_content["raw"]["numOfRegistrants"] == 42


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get("https://api.topcoder.com/v6/challenges").mock(return_value=httpx.Response(429, headers={"Retry-After": "3"}))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 3
