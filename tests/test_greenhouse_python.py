"""Greenhouse Job Board API: keyless GETs for one board (config board_token); apply needs the employer key."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "greenhouse.json").read_text(encoding="utf-8"))
BASE = "https://boards-api.greenhouse.io/v1/boards/vaulttec/jobs"
JOB = {"id": 127817, "internal_job_id": 144381, "title": "Vault Designer", "updated_at": "2016-01-14T10:55:28-05:00", "location": {"name": "NYC"},
       "absolute_url": "https://boards.greenhouse.io/vaulttec/jobs/127817", "company_name": "Vault-Tec", "first_published": "2016-01-10T09:00:00-05:00",
       "content": "This is the job description.", "departments": [{"id": 13583, "name": "Department of Departments"}], "offices": []}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"board_token": "vaulttec"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_search_and_get_posting_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_lists_the_board_with_content_and_meta_total():
    respx.get(BASE).mock(return_value=httpx.Response(200, json={"jobs": [JOB], "meta": {"total": 1}}))
    res = await _server().call_tool("search", {"query": "designer", "location": "NYC"})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "127817" and p["title"] == "Vault Designer" and p["company"] == "Vault-Tec" and p["location"] == "NYC"
    assert p["url"] == "https://boards.greenhouse.io/vaulttec/jobs/127817" and p["posted_at"].startswith("2016-01-10") and p["raw"]["internal_job_id"] == 144381
    assert sc["total"] == 1 and sc["next_page"] is None
    assert dict(respx.calls.last.request.url.params) == {"content": "true"}
    assert "Authorization" not in respx.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_maps_the_first_pay_range_in_cents():
    body = {**JOB, "pay_input_ranges": [{"min_cents": 5000000, "max_cents": 7500000, "currency_type": "USD", "title": "NYC Salary Range"}]}
    respx.get(f"{BASE}/127817").mock(return_value=httpx.Response(200, json=body))
    res = await _server().call_tool("get_posting", {"id": "127817"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["salary_min"] == 5000000 and sc["salary_max"] == 7500000 and sc["currency"] == "USD" and sc["description"] == "This is the job description."
    assert respx.calls.last.request.url.params["pay_transparency"] == "true"


@pytest.mark.asyncio
@respx.mock
async def test_missing_post_and_rate_limit_are_is_error_results():
    respx.get(f"{BASE}/1").mock(return_value=httpx.Response(404, json={"status": 404, "error": "Job not found"}))
    res = await _server().call_tool("get_posting", {"id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
    respx.get(BASE).mock(return_value=httpx.Response(429, headers={"Retry-After": "5"}))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 5
