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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "jobicy.json").read_text(encoding="utf-8"))
SEARCH = "https://jobicy.com/api/v2/remote-jobs"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered_for_the_keyless_api():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]
    assert tools[0].annotations.read_only_hint is True and "location slug" in tools[0].description


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_documented_fields_including_salary():
    respx.get(SEARCH).mock(return_value=httpx.Response(200, json={
        "jobs": [{"id": 123456, "url": "https://jobicy.com/jobs/123456-python-developer", "jobTitle": "Python Developer", "companyName": "Acme",
                  "companyLogo": "https://jobicy.com/data/acme.png", "jobIndustry": ["Engineering"], "jobType": ["full-time"], "jobGeo": "USA",
                  "jobLevel": "Senior", "jobExcerpt": "Build APIs ...", "jobDescription": "<p>Build APIs ...</p>", "pubDate": "2026-09-01 10:15:00",
                  "salaryMin": 120000, "salaryMax": 150000, "salaryCurrency": "USD", "salaryPeriod": "yearly"}]}))
    res = await _server().call_tool("search", {"query": "python", "location": "usa"})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "123456" and p["title"] == "Python Developer" and p["company"] == "Acme" and p["location"] == "USA"
    assert p["salary_min"] == 120000 and p["salary_max"] == 150000 and p["currency"] == "USD" and p["posted_at"] == "2026-09-01 10:15:00"
    assert res.structured_content["total"] is None and res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["tag"] == "python" and req.url.params["geo"] == "usa" and req.url.params["count"] == "25"
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get(SEARCH).mock(return_value=httpx.Response(429))
    res = await _server().call_tool("search", {"query": "python"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and "retry_after_seconds" not in res.structured_content
