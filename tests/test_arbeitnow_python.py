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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "arbeitnow.json").read_text(encoding="utf-8"))
FEED = "https://www.arbeitnow.com/api/job-board-api"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered_for_the_keyless_feed():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]
    assert tools[0].annotations.read_only_hint is True and "filter the returned postings client-side" in tools[0].description


@pytest.mark.asyncio
@respx.mock
async def test_search_pages_the_feed_and_maps_documented_fields():
    respx.get(FEED).mock(return_value=httpx.Response(200, json={
        "data": [{"slug": "python-developer-berlin-123", "company_name": "Acme GmbH", "title": "Python Developer", "description": "<p>Wir suchen ...</p>",
                  "remote": True, "url": "https://www.arbeitnow.com/jobs/companies/acme/python-developer-berlin-123", "tags": ["Python"],
                  "job_types": ["Full time"], "location": "Berlin", "created_at": 1756721700}],
        "links": {"first": FEED + "?page=1", "last": None, "prev": None, "next": FEED + "?page=2"},
        "meta": {"current_page": 1, "path": FEED, "per_page": 100, "to": 100}}))
    res = await _server().call_tool("search", {"query": "python", "page": 1})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "python-developer-berlin-123" and p["company"] == "Acme GmbH" and p["location"] == "Berlin"
    assert p["url"].endswith("/python-developer-berlin-123") and p["raw"]["remote"] is True and p["raw"]["created_at"] == 1756721700
    assert "posted_at" not in p  # created_at's type is not documented, so it stays raw
    req = respx.calls.last.request
    assert req.url.params["page"] == "1" and "query" not in req.url.params and "search" not in req.url.params  # only page is documented
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_platform_failure_is_an_is_error_result():
    respx.get(FEED).mock(return_value=httpx.Response(503, text="Service Unavailable"))
    res = await _server().call_tool("search", {"query": "python"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error" and res.structured_content["http_status"] == 503
