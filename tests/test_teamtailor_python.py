"""Teamtailor JSON:API: 'Token token=' key, required X-Api-Version header, per-stack host, page[number]/page[size]."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "teamtailor.json").read_text(encoding="utf-8"))
KEY = "tt_public_key_abc123xyz"
JOB = {"id": "1", "type": "jobs", "attributes": {"title": "Backend Developer", "body": "<p>Ship it</p>", "created-at": None, "min-salary": 40000,
                                                 "max-salary": 55000, "currency": "SEK", "salary-time-unit": "monthly", "remote-status": "hybrid"},
       "links": {"careersite-job-url": "https://career.example.com/jobs/1-backend-developer", "careersite-job-apply-url": "https://career.example.com/jobs/1/applications/new"}}


def _server(host="api.teamtailor.com"):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": KEY, "api_host": host}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "me", "search"]
    assert set(SPEC["adapter"]["not_offered"]) == {"apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_token_header_version_filters_and_paging():
    respx.get("https://api.teamtailor.com/v1/jobs").mock(return_value=httpx.Response(200, json={"data": [JOB], "meta": {"record-count": 41, "page-count": 5}}))
    res = await _server().call_tool("search", {"query": "backend", "page": 2, "limit": 50})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "1" and p["title"] == "Backend Developer" and p["url"].endswith("/jobs/1-backend-developer") and p["description"] == "<p>Ship it</p>"
    assert p["salary_min"] == 40000 and p["salary_max"] == 55000 and p["currency"] == "SEK" and p["posted_at"] is None
    assert sc["total"] == 41
    req = respx.calls.last.request
    assert req.headers["Authorization"] == f"Token token={KEY}" and req.headers["X-Api-Version"] == "20240904"
    assert req.url.params["filter[status]"] == "published" and req.url.params["filter[feed]"] == "public"
    assert req.url.params["page[number]"] == "2" and req.url.params["page[size]"] == "30"


@pytest.mark.asyncio
@respx.mock
async def test_na_stack_get_posting_unwraps_data():
    respx.get("https://api.na.teamtailor.com/v1/jobs/1").mock(return_value=httpx.Response(200, json={"data": JOB}))
    res = await _server("api.na.teamtailor.com").call_tool("get_posting", {"id": "1"})
    assert res.is_error is False and res.structured_content["title"] == "Backend Developer"


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_auth_error_without_the_key():
    respx.get("https://api.teamtailor.com/v1/jobs").mock(return_value=httpx.Response(401, json={"errors": [{"title": f"Invalid token {KEY}"}]}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert KEY not in json.dumps(res.structured_content)
