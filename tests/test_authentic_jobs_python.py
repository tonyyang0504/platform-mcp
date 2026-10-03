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

SPEC = json.loads((ROOT / "catalog" / "deals" / "authentic_jobs.json").read_text(encoding="utf-8"))
BASE = "https://authenticjobs.com/wp-json/wp/v2"

# job_listing row as served by GET /wp-json/wp/v2/job-listings (opened 2026-09-25), trimmed
ROW = {
    "id": 36676, "date_gmt": "2026-08-04T16:23:50", "status": "publish", "type": "job_listing",
    "link": "https://authenticjobs.com/job/36676/discord-product-designer-growth/",
    "title": {"rendered": "Product Designer, Growth"}, "content": {"rendered": "<p>Discord has…</p>", "protected": False},
    "meta": {"_job_location": "San Francisco Bay Area", "_application": "https://job-boards.greenhouse.io/discord/jobs/8674411002",
             "_company_name": "Discord", "_job_salary": "", "_filled": 0},
    "job-categories": [21], "job-types": [2],
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list_is_read_only_search_and_get():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "submit_bid", "withdraw_bid", "bid_status", "list_messages", "send_message", "credits"}


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_wp_collection_params_and_maps_rows():
    route = respx.get(f"{BASE}/job-listings").mock(return_value=httpx.Response(200, json=[ROW]))
    res = await _server().call_tool("search_postings", {"query": "designer", "category": "21", "page": 2, "limit": 5, "min_budget": 1000})
    assert res.is_error is False
    q = dict(route.calls.last.request.url.params)
    assert q == {"search": "designer", "job-categories": "21", "page": "2", "per_page": "5"}
    p = res.structured_content["postings"][0]
    assert p["id"] == "36676" and p["title"] == "Product Designer, Growth" and p["buyer"] == "Discord"
    assert p["url"].endswith("/discord-product-designer-growth/") and p["posted_at"] == "2026-08-04T16:23:50"
    assert p["raw"]["meta"]["_application"].startswith("https://job-boards.greenhouse.io/")
    assert res.structured_content["next_page"] is None


@pytest.mark.asyncio
@respx.mock
async def test_per_page_is_capped_at_100():
    route = respx.get(f"{BASE}/job-listings").mock(return_value=httpx.Response(200, json=[]))
    res = await _server().call_tool("search_postings", {"limit": 100})
    assert res.is_error is False and res.structured_content["postings"] == []
    assert route.calls.last.request.url.params["per_page"] == "100"


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_and_unknown_id():
    respx.get(f"{BASE}/job-listings/36676").mock(return_value=httpx.Response(200, json=ROW))
    respx.get(f"{BASE}/job-listings/1").mock(return_value=httpx.Response(404, json={"code": "rest_post_invalid_id", "message": "Invalid post ID.", "data": {"status": 404}}))
    ok = await _server().call_tool("get_posting", {"id": "36676"})
    assert ok.is_error is False and ok.structured_content["title"] == "Product Designer, Growth"
    bad = await _server().call_tool("get_posting", {"id": "1"})
    assert bad.is_error is True and bad.structured_content["error"] == "not_found"
