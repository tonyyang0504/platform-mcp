"""Breezy HR v3: employer PAT (Bearer), company-scoped positions list/get, /user probe."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "breezy_hr.json").read_text(encoding="utf-8"))
BASE = "https://api.breezy.hr/v3"
TOKEN = "breezy_pat_secret123456"
POS = {"_id": "a3f9c1d2e4b5", "name": "Backend Engineer", "state": "published", "type": {"id": "fullTime", "name": "Full-Time"},
       "location": {"country": {"id": "US", "name": "United States"}, "city": "Austin", "is_remote": False, "name": "Austin, TX"},
       "description": "<p>Build APIs</p>", "creation_date": "2026-09-01T10:00:00.000Z", "salary": {"from": 120000, "to": 150000, "period": "year", "currency": "USD"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_token": TOKEN, "company_id": "c0ffee123456"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "me", "search"]
    assert set(SPEC["adapter"]["not_offered"]) == {"apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_lists_published_positions_with_bearer_and_paging():
    respx.get(f"{BASE}/company/c0ffee123456/positions").mock(return_value=httpx.Response(200, json=[POS]))
    res = await _server().call_tool("search", {"query": "backend", "page": 2, "limit": 80})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "a3f9c1d2e4b5" and p["title"] == "Backend Engineer" and p["location"] == "Austin, TX"
    assert p["salary_min"] == 120000 and p["salary_max"] == 150000 and p["currency"] == "USD" and p["posted_at"].startswith("2026-09-01")
    req = respx.calls.last.request
    assert req.headers["Authorization"] == f"Bearer {TOKEN}"
    assert req.url.params["state"] == "published" and req.url.params["page"] == "2" and req.url.params["page_size"] == "50"
    assert "query" not in req.url.params


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_and_me():
    respx.get(f"{BASE}/company/c0ffee123456/position/a3f9c1d2e4b5").mock(return_value=httpx.Response(200, json=POS))
    res = await _server().call_tool("get_posting", {"id": "a3f9c1d2e4b5"})
    assert res.is_error is False and res.structured_content["title"] == "Backend Engineer" and res.structured_content["description"] == "<p>Build APIs</p>"
    respx.get(f"{BASE}/user").mock(return_value=httpx.Response(200, json={"_id": "u1", "email_address": "r@example.com", "name": "Rae"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True and res.structured_content["account"]["name"] == "Rae"


@pytest.mark.asyncio
@respx.mock
async def test_forbidden_company_is_auth_error_without_the_token():
    respx.get(f"{BASE}/company/c0ffee123456/positions").mock(return_value=httpx.Response(
        403, json={"error": {"type": "companyMembershipRequired", "message": f"token {TOKEN} is not a member"}}))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert TOKEN not in json.dumps(res.structured_content)
