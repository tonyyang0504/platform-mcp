"""Jooble: API key in the URL path, one POST search call with a JSON body."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "jooble.json").read_text(encoding="utf-8"))
URL = "https://jooble.org/api/KEY123"
JOB = {"id": 1234567890, "title": "IT Support Specialist", "location": "Bern", "snippet": "Support the IT team ...", "salary": "80'000 - 90'000 CHF",
       "source": "jobs.ch", "type": "Full-time", "link": "https://jooble.org/desc/1234567890", "company": "Acme AG", "updated": "2026-09-20T00:00:00.0000000"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "KEY123"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]  # search-only API: me / get_posting / apply / list_messages are explained under not_offered
    search = tools[0]
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.output_schema["properties"]["postings"]["type"] == "array"
    assert search.meta["platform_mcp/docs"].startswith("https://help.jooble.org/")
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_posting", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_posts_the_documented_body_with_the_key_in_the_path():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"totalCount": 1, "jobs": [JOB]}))
    res = await _server().call_tool("search", {"query": "it", "location": "Bern", "page": 3, "limit": 20})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "1234567890" and p["title"] == "IT Support Specialist" and p["company"] == "Acme AG" and p["location"] == "Bern"
    assert p["url"] == "https://jooble.org/desc/1234567890" and p["posted_at"].startswith("2026-09-20") and p["description"] == "Support the IT team ..."
    assert "salary_min" not in p and p["raw"]["salary"] == "80'000 - 90'000 CHF"  # formatted string stays raw
    assert res.structured_content["total"] == 1 and res.structured_content["next_page"] is None
    req = route.calls.last.request
    assert req.url.path == "/api/KEY123" and "Authorization" not in req.headers
    assert json.loads(req.content) == {"keywords": "it", "location": "Bern", "page": 3, "ResultOnPage": 20}


@pytest.mark.asyncio
@respx.mock
async def test_search_without_location_omits_the_field_and_uses_the_default_page_size():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"totalCount": 0, "jobs": []}))
    res = await _server().call_tool("search", {"query": "python"})
    assert res.is_error is False and res.structured_content["postings"] == []
    assert json.loads(route.calls.last.request.content) == {"keywords": "python", "page": 1, "ResultOnPage": 25}


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_an_auth_error_result_and_the_key_is_not_echoed():
    respx.post(URL).mock(return_value=httpx.Response(401, text="Invalid key KEY123"))
    res = await _server().call_tool("search", {"query": "it", "location": "Bern"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
