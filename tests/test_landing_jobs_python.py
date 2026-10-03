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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "landing_jobs.json").read_text(encoding="utf-8"))
BASE = "https://landing.jobs/api/v1"
JOB = {"id": 19513, "title": "SQL Bridge Engineer", "currency_code": "EUR", "gross_salary_low": 80000, "gross_salary_high": 95000,
       "role_description": "<div>First tech hire</div>", "published_at": "2026-01-26T14:51:00.487Z", "remote": False,
       "tags": ["SQL", "Python"], "url": "https://landing.jobs/at/oralpro-llc/sql-bridge-engineer",
       "locations": [{"city": "Lisbon", "country_code": "PT"}]}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_keyless_tools_follow_the_vocabulary():
    names = sorted(t.name for t in await _server().list_tools())
    assert names == ["get_posting", "search"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_offset_and_limit_and_maps_fields():
    route = respx.get(f"{BASE}/jobs").mock(return_value=httpx.Response(200, json=[JOB]))
    res = await _server().call_tool("search", {"query": "sql", "page": 3, "limit": 10})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "19513" and p["title"] == "SQL Bridge Engineer" and p["location"] == "Lisbon"
    assert p["salary_min"] == 80000 and p["salary_max"] == 95000 and p["currency"] == "EUR"
    assert p["posted_at"] == "2026-01-26T14:51:00.487Z" and p["raw"]["tags"] == ["SQL", "Python"]
    q = route.calls.last.request.url.params
    assert q["offset"] == "20" and q["limit"] == "10" and "query" not in q
    assert "Authorization" not in route.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_limit_is_capped_at_the_documented_maximum():
    route = respx.get(f"{BASE}/jobs").mock(return_value=httpx.Response(200, json=[]))
    res = await _server().call_tool("search", {"query": "x", "limit": 100})
    assert res.is_error is False and res.structured_content["postings"] == []
    assert route.calls.last.request.url.params["limit"] == "50"


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_reads_one_job():
    respx.get(f"{BASE}/jobs/19513").mock(return_value=httpx.Response(200, json=JOB))
    res = await _server().call_tool("get_posting", {"id": "19513"})
    assert res.is_error is False
    assert res.structured_content["id"] == "19513" and res.structured_content["url"].endswith("/sql-bridge-engineer")


@pytest.mark.asyncio
@respx.mock
async def test_missing_job_is_not_found():
    respx.get(f"{BASE}/jobs/1").mock(return_value=httpx.Response(404, json={"error": "not found"}))
    res = await _server().call_tool("get_posting", {"id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
