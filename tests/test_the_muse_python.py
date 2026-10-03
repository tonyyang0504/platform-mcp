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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "the_muse.json").read_text(encoding="utf-8"))
JOBS = "https://www.themuse.com/api/public/jobs"
JOB = {"id": 12345678, "name": "Senior Python Engineer", "contents": "<p>You will ...</p>", "publication_date": "2026-09-01T10:15:00Z",
       "locations": [{"name": "New York, NY"}], "categories": [{"name": "Software Engineering"}], "levels": [{"name": "Senior Level", "short_name": "senior"}],
       "company": {"id": 100, "short_name": "acme", "name": "Acme"}, "refs": {"landing_page": "https://www.themuse.com/jobs/acme/senior-python-engineer"}}


def _server(creds):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server({}).list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "me", "search"]
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and "pages hold 20 results" in search.description
    assert SPEC["adapter"]["auth"]["fields"][0]["required"] is False  # the key is optional


@pytest.mark.asyncio
@respx.mock
async def test_search_without_a_key_maps_documented_fields_and_sends_no_credential():
    respx.get(JOBS).mock(return_value=httpx.Response(200, json={"page": 1, "page_count": 50, "results": [JOB]}))
    res = await _server({}).call_tool("search", {"query": "python", "location": "New York, NY"})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "12345678" and p["title"] == "Senior Python Engineer" and p["company"] == "Acme" and p["location"] == "New York, NY"
    assert p["url"] == "https://www.themuse.com/jobs/acme/senior-python-engineer" and p["posted_at"] == "2026-09-01T10:15:00Z"
    req = respx.calls.last.request
    assert req.url.params["page"] == "1" and req.url.params["location"] == "New York, NY"
    assert "api_key" not in req.url.params and "query" not in req.url.params  # no keyword filter is documented


@pytest.mark.asyncio
@respx.mock
async def test_registered_key_travels_as_the_api_key_query_parameter():
    respx.get(JOBS + "/12345678").mock(return_value=httpx.Response(200, json=JOB))
    res = await _server({"api_key": "k"}).call_tool("get_posting", {"id": "12345678"})
    assert res.is_error is False and res.structured_content["id"] == "12345678"
    assert respx.calls.last.request.url.params["api_key"] == "k"


@pytest.mark.asyncio
@respx.mock
async def test_hourly_quota_exceeded_403_is_an_is_error_result():
    respx.get(JOBS).mock(return_value=httpx.Response(403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Limit": "500"}, text="Forbidden"))
    res = await _server({}).call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403
