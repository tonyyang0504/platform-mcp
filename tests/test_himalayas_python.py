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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "himalayas.json").read_text(encoding="utf-8"))
FEED = "https://himalayas.app/jobs/api"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered_for_the_keyless_feed():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]
    assert tools[0].annotations.read_only_hint is True and tools[0].meta["platform_mcp/endpoint"] == "/jobs/api"


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_documented_fields_and_uses_offset_paging():
    respx.get(FEED).mock(return_value=httpx.Response(200, json={
        "totalCount": 103219, "nextCursor": "eyJvZmZzZXQiOjI1fQ",
        "jobs": [{"title": "Python Developer", "excerpt": "Build APIs ...", "description": "<p>Build APIs ...</p>", "companyName": "Acme", "companySlug": "acme",
                  "companyLogo": "https://himalayas.app/companies/acme/logo.png", "applicationLink": "https://himalayas.app/companies/acme/jobs/python-developer",
                  "guid": "https://himalayas.app/companies/acme/jobs/python-developer", "pubDate": 1756721700, "expiryDate": 1759313700,
                  "employmentType": "Full Time", "seniority": ["Senior"], "categories": ["Backend"], "parentCategories": ["Engineering"],
                  "locationRestrictions": ["United States"], "timezoneRestrictions": [], "minSalary": 120000, "maxSalary": 150000,
                  "currency": "USD", "salaryPeriod": "yearly"}]}))
    res = await _server().call_tool("search", {"query": "python", "page": 2})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "https://himalayas.app/companies/acme/jobs/python-developer" and p["company"] == "Acme" and p["location"] == "United States"
    assert p["salary_min"] == 120000 and p["salary_max"] == 150000 and p["currency"] == "USD" and "posted_at" not in p and p["raw"]["pubDate"] == 1756721700
    assert res.structured_content["total"] == 103219 and res.structured_content["next_page"] is None  # one row < limit
    req = respx.calls.last.request
    assert req.url.params["limit"] == "25" and req.url.params["offset"] == "25" and "query" not in req.url.params
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get(FEED).mock(return_value=httpx.Response(429, headers={"Retry-After": "10"}))
    res = await _server().call_tool("search", {"query": "python"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 10
