"""Homerun Public API v2: Bearer key, the key owner's vacancies (literal filter/include query kept beside page/perPage)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "homerun.json").read_text(encoding="utf-8"))
BASE = "https://api.homerun.co/v2/vacancies"
KEY = "hr_live_secretkey987"
VAC = {"id": "job_SnhUsAg1QwTRFIRNUfM6", "status": "public", "title": "Product Designer", "description": "Design things", "type": "Contracted",
       "location_type": "on-site", "location": {"name": "Amsterdam HQ", "country": "NL", "city": "Amsterdam"}, "department": {"name": "Design"},
       "salary_indication": {"experience_level": "entry", "currency": "eur", "salary_value": "45000.00", "max_salary_value": "60000.00", "time_period": "year"},
       "created_at": "2026-09-20T10:00:00Z"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": KEY}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "me", "search"]
    assert set(SPEC["adapter"]["not_offered"]) == {"apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_keeps_the_literal_filter_and_includes_and_adds_paging():
    respx.get(BASE).mock(return_value=httpx.Response(200, json={"data": [VAC]}))
    res = await _server().call_tool("search", {"query": "designer", "page": 3, "limit": 20})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "job_SnhUsAg1QwTRFIRNUfM6" and p["title"] == "Product Designer" and p["location"] == "Amsterdam HQ"
    assert p["posted_at"] == "2026-09-20T10:00:00Z" and p["raw"]["salary_indication"]["salary_value"] == "45000.00"
    req = respx.calls.last.request
    assert req.headers["Authorization"] == f"Bearer {KEY}"
    assert req.url.params["filter[status]"] == "public" and req.url.params.get_list("include[]") == ["location", "department", "salaryIndication"]
    assert req.url.params["page"] == "3" and req.url.params["perPage"] == "20" and "q" not in req.url.params


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_unwraps_data():
    respx.get(f"{BASE}/job_SnhUsAg1QwTRFIRNUfM6").mock(return_value=httpx.Response(200, json={"data": VAC}))
    res = await _server().call_tool("get_posting", {"id": "job_SnhUsAg1QwTRFIRNUfM6"})
    assert res.is_error is False and res.structured_content["title"] == "Product Designer" and res.structured_content["description"] == "Design things"
    assert "page_content" in respx.calls.last.request.url.params.get_list("include[]")


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_auth_error_and_is_scrubbed():
    respx.get(BASE).mock(return_value=httpx.Response(401, json={"message": f"Invalid key {KEY}"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert KEY not in json.dumps(res.structured_content)
    assert respx.calls.last.request.url.params["perPage"] == "1"
