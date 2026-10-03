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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "remotive.json").read_text(encoding="utf-8"))
SEARCH = "https://remotive.com/api/remote-jobs"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered_for_the_keyless_feed():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]
    search = tools[0]
    assert search.annotations.read_only_hint is True and search.title == "Search job postings"
    assert "fetch at most ~4 times a day" in search.description
    assert SPEC["adapter"]["rate_per_second"] == 0.01


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_documented_fields():
    respx.get(SEARCH).mock(return_value=httpx.Response(200, json={
        "job-count": 1,
        "jobs": [{"id": 1900000, "url": "https://remotive.com/remote-jobs/software-dev/python-developer-1900000", "title": "Python Developer",
                  "company_name": "Acme", "company_logo": "https://remotive.com/job/1900000/logo", "category": "Software Development",
                  "job_type": "full_time", "publication_date": "2026-09-01T10:15:00", "candidate_required_location": "Worldwide",
                  "salary": "$80k - $100k", "description": "<p>We build ...</p>"}]}))
    res = await _server().call_tool("search", {"query": "python"})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "1900000" and p["company"] == "Acme" and p["location"] == "Worldwide" and p["posted_at"] == "2026-09-01T10:15:00"
    assert "salary_min" not in p and p["raw"]["salary"] == "$80k - $100k"  # free-text salary stays raw
    assert res.structured_content["total"] == 1 and res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["search"] == "python" and req.url.params["limit"] == "25" and "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get(SEARCH).mock(return_value=httpx.Response(429, headers={"Retry-After": "60"}))
    res = await _server().call_tool("search", {"query": "python"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 60
