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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "authentic_jobs.json").read_text(encoding="utf-8"))
BASE = "https://authenticjobs.com/wp-json/wp/v2"
ROW = {"id": 36676, "date_gmt": "2026-08-04T16:23:50", "status": "publish", "type": "job_listing",
       "link": "https://authenticjobs.com/job/36676/product-designer/", "title": {"rendered": "Product Designer, Growth"},
       "content": {"rendered": "<p>Design things.</p>"},
       "meta": {"_company_name": "Discord", "_application": "https://example.invalid/apply", "_job_location": "San Francisco Bay Area"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_keyless_search_and_get_posting_are_offered():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_posting", "search"]


@pytest.mark.asyncio
@respx.mock
async def test_search_uses_the_wp_rest_listing_route():
    route = respx.get(BASE + "/job-listings").mock(return_value=httpx.Response(200, json=[ROW, {**ROW, "id": 2}]))
    res = await _server().call_tool("search", {"query": "designer", "location": "Paris", "page": 3, "limit": 2})
    assert res.is_error is False, res.structured_content
    p = res.structured_content["postings"]
    assert [x["id"] for x in p] == ["36676", "2"] and res.structured_content["next_page"] == 4
    assert p[0]["title"] == "Product Designer, Growth" and p[0]["company"] == "Discord" and p[0]["location"] == 'San Francisco Bay Area'
    assert p[0]["posted_at"] == "2026-08-04T16:23:50" and p[0]["description"] == "<p>Design things.</p>"
    assert dict(route.calls.last.request.url.params) == {"search": "designer", "page": "3", "per_page": "2"}


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_reads_one_listing_and_unknown_is_not_found():
    respx.get(BASE + "/job-listings/36676").mock(return_value=httpx.Response(200, json=ROW))
    respx.get(BASE + "/job-listings/9").mock(return_value=httpx.Response(404, json={"code": "rest_post_invalid_id"}))
    ok = await _server().call_tool("get_posting", {"id": "36676"})
    assert ok.is_error is False and ok.structured_content["url"].endswith("/product-designer/")
    assert ok.structured_content["raw"]["meta"]["_application"] == "https://example.invalid/apply"
    bad = await _server().call_tool("get_posting", {"id": "9"})
    assert bad.is_error is True and bad.structured_content["error"] == "not_found"
