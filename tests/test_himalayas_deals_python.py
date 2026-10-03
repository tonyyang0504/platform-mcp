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

SPEC = json.loads((ROOT / "catalog" / "deals" / "himalayas.json").read_text(encoding="utf-8"))
URL = "https://himalayas.app/jobs/api/search"

# job as returned live on 2026-09-25 (lists trimmed)
JOB = {
    "title": "Senior React Native Developer", "excerpt": "Are you a talented Senior Developer …", "companyName": "lemon.io", "companySlug": "lemon-io",
    "employmentType": "Contractor", "minSalary": None, "maxSalary": None, "salaryPeriod": "annual", "currency": "USD",
    "categories": ["React-Native-Developer"], "description": "<p>…</p>", "pubDate": 1789127040, "expiryDate": 1791719039,
    "applicationLink": "https://himalayas.app/companies/lemon-io/jobs/senior-react-native-developer-5236230554",
    "guid": "https://himalayas.app/companies/lemon-io/jobs/senior-react-native-developer-5236230554",
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_postings_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search_postings"] and tools[0].annotations.read_only_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_q_employment_type_page_and_recent_sort():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"offset": 20, "limit": 20, "totalCount": 5000, "jobs": [JOB] * 20}))
    res = await _server().call_tool("search_postings", {"query": "react native", "category": "Contractor", "page": 2, "min_budget": 1000})
    assert res.is_error is False
    assert dict(route.calls.last.request.url.params) == {"q": "react native", "employment_type": "Contractor", "page": "2", "sort": "recent"}
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == JOB["guid"] and p["buyer"] == "lemon.io" and p["skills"] == ["React-Native-Developer"] and p["url"] == JOB["applicationLink"]
    assert p["budget_min"] is None and p["currency"] == "USD" and p["raw"]["pubDate"] == 1789127040
    assert sc["total"] == 5000 and sc["next_page"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_reported():
    respx.get(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}, json={"error": "Too many requests"}))
    res = await _server().call_tool("search_postings", {"query": "go"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
