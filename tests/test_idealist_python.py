import base64
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "idealist.json").read_text(encoding="utf-8"))
BASE = "https://www.idealist.org/api/v1"
KEY = "9e11d62224ab48c79432fae431397620"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": KEY}, 50, "test")
    return build_server(SPEC, transport=t)


def _job(i, updated):
    return {"id": f"job{i}", "firstPublished": "2019-06-23T18:02:07.212112Z", "updated": updated, "name": f"Role {i}",
            "url": {"en": f"https://www.idealist.org/en/nonprofit-job/{i}"}, "isPublished": True}


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_posting", "me", "search"]


@pytest.mark.asyncio
@respx.mock
async def test_search_uses_basic_auth_and_since_cursor():
    route = respx.get(f"{BASE}/listings/jobs").mock(return_value=httpx.Response(200, json={"jobs": [_job(1, "2019-06-23T18:02:07.269921Z")], "hasMore": False}))
    res = await _server().call_tool("search", {"query": "director", "cursor": "2019-06-01T00:00:00Z"})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "job1" and p["title"] == "Role 1" and p["url"].endswith("/1") and p["raw"]["updated"] == "2019-06-23T18:02:07.269921Z"
    assert res.structured_content["next_cursor"] is None and res.structured_content["next_page"] is None
    req = route.calls.last.request
    assert req.url.params["since"] == "2019-06-01T00:00:00Z" and "query" not in req.url.params
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(f"{KEY}:".encode()).decode()
    assert req.headers["Accept"] == "application/json"


@pytest.mark.asyncio
@respx.mock
async def test_full_page_hands_back_the_last_updated_as_cursor():
    jobs = [_job(i, f"2020-01-01T00:00:{i:02d}.000000Z") for i in range(100)]
    route = respx.get(f"{BASE}/listings/jobs").mock(return_value=httpx.Response(200, json={"jobs": jobs, "hasMore": True}))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.structured_content["next_cursor"] == "2020-01-01T00:00:99.000000Z"
    assert "since" not in route.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_maps_details():
    respx.get(f"{BASE}/listings/jobs/f976").mock(return_value=httpx.Response(200, json={"job": {
        "id": "f976", "name": "Executive Director", "description": "<p>x</p>", "firstPublished": "2019-07-23T17:34:23.848076Z",
        "org": {"name": "Example Organization"}, "address": {"full": "123 Broadway, New York, NY, United States"},
        "salaryMinimum": "50000.00", "salaryCurrency": "USD", "url": {"en": "https://www.idealist.org/en/nonprofit-job/f976"}}}))
    res = await _server().call_tool("get_posting", {"id": "f976"})
    sc = res.structured_content
    assert res.is_error is False and sc["company"] == "Example Organization" and sc["location"].startswith("123 Broadway") and sc["currency"] == "USD"


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_auth_error_and_scrubbed():
    respx.get(f"{BASE}/listings/jobs").mock(return_value=httpx.Response(401, json={"detail": f"bad key {KEY}"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert KEY not in json.dumps(res.structured_content)
