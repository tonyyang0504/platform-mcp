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

SPEC = json.loads((ROOT / "catalog" / "deals" / "roblox_devforum_collaboration.json").read_text(encoding="utf-8"))
BASE = "https://devforum.roblox.com"

# Discourse search / topic shapes as returned live on 2026-09-25, trimmed
TOPIC = {"id": 4884226, "title": "[HIRING] Scripter for a tycoon", "slug": "hiring-scripter", "created_at": "2026-09-20T16:07:54.000Z",
         "excerpt": "Looking for a scripter …", "tags": ["scripter", "builder"], "category_id": 82}
FULL = {**TOPIC, "details": {"created_by": {"id": 1, "username": "StudioOwner"}},
        "post_stream": {"posts": [{"id": 9, "post_number": 1, "cooked": "<p>Paying 50k Robux</p>", "username": "StudioOwner"}]}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_are_read_only_search_and_get():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]
    assert all(t.annotations.read_only_hint for t in tools)


@pytest.mark.asyncio
@respx.mock
async def test_search_scopes_query_to_the_jobs_category():
    route = respx.get(f"{BASE}/search.json").mock(return_value=httpx.Response(200, json={"topics": [TOPIC], "posts": [], "grouped_search_result": {"more_full_page_results": True}}))
    res = await _server().call_tool("search_postings", {"query": "scripter", "page": 2, "category": "x", "min_budget": 5})
    assert res.is_error is False
    assert dict(route.calls.last.request.url.params) == {"q": "scripter category:82 order:latest", "page": "2"}
    p = res.structured_content["postings"][0]
    assert p["id"] == "4884226" and p["title"].startswith("[HIRING]") and p["posted_at"] == "2026-09-20T16:07:54.000Z"
    assert p["skills"] == ["scripter", "builder"]


@pytest.mark.asyncio
@respx.mock
async def test_search_without_query_sends_no_q():
    route = respx.get(f"{BASE}/search.json").mock(return_value=httpx.Response(200, json={"grouped_search_result": None}))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is False and res.structured_content["postings"] == []
    assert "q" not in route.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_reads_creator_and_first_post_and_404():
    respx.get(f"{BASE}/t/4884226.json").mock(return_value=httpx.Response(200, json=FULL))
    respx.get(f"{BASE}/t/1.json").mock(return_value=httpx.Response(404, json={"errors": ["The requested URL or resource could not be found."], "error_type": "not_found"}))
    ok = await _server().call_tool("get_posting", {"id": "4884226"})
    assert ok.is_error is False and ok.structured_content["buyer"] == "StudioOwner" and ok.structured_content["description"] == "<p>Paying 50k Robux</p>"
    miss = await _server().call_tool("get_posting", {"id": "1"})
    assert miss.is_error is True and miss.structured_content["error"] == "not_found"
