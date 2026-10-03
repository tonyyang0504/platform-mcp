"""Platsbanken (Arbetsförmedlingen JobSearch API): keyless /search with offset/limit and /ad/{id}."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "platsbanken.json").read_text(encoding="utf-8"))
BASE = "https://jobsearch.api.jobtechdev.se"
AD = {"id": "31403584", "headline": "Python Engineer", "employer": {"name": "Semicon Service Nordic AB", "workplace": "Malmö, Sweden"},
      "workplace_address": {"municipality": "Malmö", "region": "Skåne län", "country": "Sverige"}, "webpage_url": "https://arbetsformedlingen.se/platsbanken/annonser/31403584",
      "publication_date": "2026-08-27T10:01:50", "description": {"text": "Assignment Overview ...", "text_formatted": "<p>Assignment Overview ...</p>"},
      "application_details": {"email": "hr@example.com", "via_af": False, "url": None}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search"]
    gp = next(t for t in tools if t.name == "get_posting")
    assert gp.annotations.read_only_hint is True and gp.input_schema["required"] == ["id"] and gp.meta["platform_mcp/endpoint"] == "/ad/{id}"
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_q_remote_offset_and_limit_without_any_credential():
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(200, json={"total": {"value": 739}, "hits": [AD]}))
    res = await _server().call_tool("search", {"query": "python", "location": "Malmö", "remote": True, "page": 3, "limit": 10})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "31403584" and p["title"] == "Python Engineer" and p["company"] == "Semicon Service Nordic AB" and p["location"] == "Malmö"
    assert p["url"].endswith("/annonser/31403584") and p["posted_at"] == "2026-08-27T10:01:50" and p["description"] == "Assignment Overview ..."
    assert sc["total"] == 739 and sc["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["q"] == "python" and req.url.params["remote"] == "true" and req.url.params["offset"] == "20" and req.url.params["limit"] == "10"
    assert "municipality" not in req.url.params and "Authorization" not in req.headers and "api-key" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_maps_the_ad_and_keeps_application_details_raw():
    respx.get(f"{BASE}/ad/31403584").mock(return_value=httpx.Response(200, json=AD))
    res = await _server().call_tool("get_posting", {"id": "31403584"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "31403584" and sc["title"] == "Python Engineer" and sc["description"] == "Assignment Overview ..."
    assert sc["raw"]["application_details"]["email"] == "hr@example.com"


@pytest.mark.asyncio
@respx.mock
async def test_missing_ad_and_rate_limit_are_is_error_results():
    respx.get(f"{BASE}/ad/1").mock(return_value=httpx.Response(404, json={"message": "Job ad not found"}))
    res = await _server().call_tool("get_posting", {"id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "not_found" and res.structured_content["http_status"] == 404
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(429, headers={"Retry-After": "5"}))
    res = await _server().call_tool("search", {"query": "python"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 5
