"""Workable SPI v3: Bearer token, per-account subdomain host, published jobs list, job by shortcode, account probe."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "workable.json").read_text(encoding="utf-8"))
BASE = "https://groove-tech.workable.com/spi/v3"
TOKEN = "wk_secret_token_4f7a9b"
JOB = {"id": "61884e2", "title": "Sales Intern", "shortcode": "GROOV003", "state": "published", "department": "Sales",
       "url": "https://groove-tech.workable.com/jobs/102268944", "application_url": "https://groove-tech.workable.com/jobs/102268944/candidates/new",
       "location": {"location_str": "Portland, Oregon, United States", "country_code": "US"}, "salary": {"salary_from": 10000, "salary_to": 20000, "salary_currency": "eur"},
       "created_at": "2015-07-01T00:00:00Z", "description": "<p>Sell</p>"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_token": TOKEN, "subdomain": "groove-tech"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "me", "search"]
    assert set(SPEC["adapter"]["not_offered"]) == {"apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_lists_published_jobs_with_bearer_and_capped_limit():
    respx.get(f"{BASE}/jobs").mock(return_value=httpx.Response(200, json={"jobs": [JOB], "paging": {"next": f"{BASE}/jobs?limit=100&since_id=2700d6df"}}))
    res = await _server().call_tool("search", {"query": "sales", "limit": 500})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "GROOV003" and p["title"] == "Sales Intern" and p["location"] == "Portland, Oregon, United States"
    assert p["salary_min"] == 10000 and p["salary_max"] == 20000 and p["currency"] == "eur" and p["description"] == "<p>Sell</p>"
    req = respx.calls.last.request
    assert req.headers["Authorization"] == f"Bearer {TOKEN}"
    assert dict(req.url.params) == {"limit": "100", "state": "published", "include_fields": "description"}


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_and_the_account_probe_on_the_shared_host():
    respx.get(f"{BASE}/jobs/GROOV003").mock(return_value=httpx.Response(200, json={**JOB, "full_description": "<p>Full</p>"}))
    res = await _server().call_tool("get_posting", {"id": "GROOV003"})
    assert res.is_error is False and res.structured_content["description"] == "<p>Full</p>"
    respx.get("https://workable.com/spi/v3/accounts/groove-tech").mock(return_value=httpx.Response(200, json={"id": "20ff5c50", "name": "Groove Tech", "subdomain": "groove-tech"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["name"] == "Groove Tech"


@pytest.mark.asyncio
@respx.mock
async def test_bad_token_is_auth_error_without_the_token():
    respx.get(f"{BASE}/jobs").mock(return_value=httpx.Response(401, json={"error": f"Not authorized: {TOKEN}"}))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert TOKEN not in json.dumps(res.structured_content)
