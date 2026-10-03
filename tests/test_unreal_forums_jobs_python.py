"""Unreal Engine forums Job Offerings (Discourse): keyless category-scoped /search.json and /t/{id}.json."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "unreal_forums_jobs.json").read_text(encoding="utf-8"))
BASE = "https://forums.unrealengine.com"
TOPIC = {"id": 613332, "title": "[PAID] C++ gameplay programmer", "slug": "paid-c-gameplay-programmer", "created_at": "2026-09-20T20:16:46.860Z",
         "excerpt": "We are looking for a gameplay programmer", "category_id": 76}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search"]
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_scopes_the_query_to_the_job_offerings_category():
    respx.get(f"{BASE}/search.json").mock(return_value=httpx.Response(200, json={"posts": [{"id": 1, "topic_id": 613332, "blurb": "..."}], "topics": [TOPIC],
                                                                                  "grouped_search_result": {"more_full_page_results": None}}))
    res = await _server().call_tool("search", {"query": "programmer", "page": 2})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "613332" and p["title"] == "[PAID] C++ gameplay programmer" and p["posted_at"].startswith("2026-09-20")
    assert p["description"] == "We are looking for a gameplay programmer" and p["raw"]["category_id"] == 76
    params = respx.calls.last.request.url.params
    assert params["q"] == "programmer #got-skills-looking-for-talent:job-offerings order:latest" and params["page"] == "2"


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_reads_the_opening_post():
    respx.get(f"{BASE}/t/613332.json").mock(return_value=httpx.Response(200, json={**TOPIC, "post_stream": {"posts": [{"id": 9, "cooked": "<p>DM me</p>"}]}}))
    res = await _server().call_tool("get_posting", {"id": "613332"})
    assert res.is_error is False and res.structured_content["description"] == "<p>DM me</p>"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get(f"{BASE}/search.json").mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}, json={"errors": ["too many requests"]}))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30
