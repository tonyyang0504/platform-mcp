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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "working_nomads.json").read_text(encoding="utf-8"))
FEED = "https://www.workingnomads.com/api/exposed_jobs/"
ROW = {"url": "https://www.workingnomads.com/job/go/1889808/", "title": "Backend Developer", "description": "<p>Remote</p>",
       "company_name": "CloudGeometry", "category_name": "Development", "tags": "python,django", "location": "Europe",
       "pub_date": "2026-09-20T10:00:00-04:00"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"] and tools[0].annotations.read_only_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_search_returns_the_whole_feed_without_parameters():
    route = respx.get(FEED).mock(return_value=httpx.Response(200, json=[ROW]))
    res = await _server().call_tool("search", {"query": "python", "location": "Europe", "page": 1})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == ROW["url"] and p["company"] == "CloudGeometry" and p["location"] == "Europe" and p["raw"]["tags"] == "python,django"
    assert dict(route.calls.last.request.url.params) == {}


@pytest.mark.asyncio
@respx.mock
async def test_upstream_failure_is_an_is_error_result():
    respx.get(FEED).mock(return_value=httpx.Response(500, text="oops"))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
