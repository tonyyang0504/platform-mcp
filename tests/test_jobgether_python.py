"""Jobgether Job Search API: keyless GET /api/v1/jobs with keyword/locations/page/limit; problem+json errors."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "jobgether.json").read_text(encoding="utf-8"))
URL = "https://jobgether.com/api/v1/jobs"
JOB = {"id": "6ab4452d865119c687e37359", "title": "AI Application Developer II", "company": "CareSource", "url": "https://jobgether.com/offer/6ab4452d865119c687e37359-ai-application-developer-ii",
       "location": "Oregon (USA)", "remote": "Full Remote", "contractType": "Full time", "experience": "Mid-level (2-5 years)", "jobFunctions": ["AI Developer"], "postedAt": "2026-09-23T21:31:25.954Z"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]  # the OpenAPI has no single-job endpoint
    search = tools[0]
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.meta["platform_mcp/docs"] == "https://jobgether.com/developers"
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_posting", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_keyword_locations_page_and_limit():
    respx.get(URL).mock(return_value=httpx.Response(200, json={"jobs": [JOB], "pagination": {"page": 2, "limit": 10, "hasMore": True}, "browseOnSiteUrl": "https://jobgether.com/search-offers?keyword=python"}))
    res = await _server().call_tool("search", {"query": "python", "location": "germany", "page": 2, "limit": 10})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "6ab4452d865119c687e37359" and p["title"] == "AI Application Developer II" and p["company"] == "CareSource"
    assert p["location"] == "Oregon (USA)" and p["url"].startswith("https://jobgether.com/offer/") and p["posted_at"] == "2026-09-23T21:31:25.954Z"
    assert "description" not in p and p["raw"]["remote"] == "Full Remote" and p["raw"]["jobFunctions"] == ["AI Developer"]
    assert sc["total"] is None and sc["next_page"] is None  # one hit on a page of 10: no further page
    req = respx.calls.last.request
    assert req.url.params["keyword"] == "python" and req.url.params["locations"] == "germany" and req.url.params["page"] == "2" and req.url.params["limit"] == "10"
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_limit_is_capped_at_25_and_a_full_page_yields_next_page():
    respx.get(URL).mock(return_value=httpx.Response(200, json={"jobs": [JOB] * 25, "pagination": {"page": 1, "limit": 25, "hasMore": True}}))
    res = await _server().call_tool("search", {"query": "react", "limit": 100})
    assert res.is_error is False and len(res.structured_content["postings"]) == 25
    assert respx.calls.last.request.url.params["limit"] == "25"  # documented cap
    res = await _server().call_tool("search", {"query": "react", "limit": 25})
    assert res.structured_content["next_page"] == 2  # a full page of 25 means there may be more (page max 10 per the docs)


@pytest.mark.asyncio
@respx.mock
async def test_unknown_location_slug_is_an_invalid_input_result_carrying_the_problem_detail():
    respx.get(URL).mock(return_value=httpx.Response(400, json={"type": "/astroapi/ai/jobs/docs#invalid_parameter", "title": "Invalid parameter", "status": 400,
                                                                  "detail": "Invalid value for 'locations': \"Germany\"", "code": "invalid_parameter", "field": "locations"},
                                                     headers={"Content-Type": "application/problem+json"}))
    res = await _server().call_tool("search", {"query": "python", "location": "Germany"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and res.structured_content["http_status"] == 400
    assert "Invalid value for 'locations'" in res.structured_content["message"]
