"""Get on Board: keyless public search (JSON:API) with expand=["company"]; job details are a private endpoint."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "getonbrd.json").read_text(encoding="utf-8"))
URL = "https://www.getonbrd.com/api/v0/search/jobs"
HIT = {"id": "web-app-full-stack-engineer-niuro-remote-4461", "type": "job", "attributes": {
    "title": "Web App Full-Stack Engineer", "description": "<p>Build ...</p>", "remote": True, "remote_modality": "fully_remote", "countries": ["Remote"],
    "min_salary": 2500, "max_salary": 4000, "published_at": 1790253211, "category_name": "Programming",
    "company": {"data": {"id": "niuro", "type": "company", "attributes": {"name": "Niuro", "description": "..."}}}},
    "links": {"public_url": "https://www.getonbrd.com/jobs/web-app-full-stack-engineer-niuro-remote-4461"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]  # GET /api/v0/jobs/{id} needs the company API key, so get_posting is not offered
    search = tools[0]
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.meta["platform_mcp/docs"] == "https://www.getonbrd.com/api-doc.html"
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_posting", "apply", "list_messages"}
    assert "ApiKeyAuth" in SPEC["adapter"]["not_offered"]["get_posting"]


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_json_api_hits_and_expands_the_company():
    respx.get(URL).mock(return_value=httpx.Response(200, json={"data": [HIT], "meta": {"page": 2, "per_page": 30, "total_pages": 310}}))
    res = await _server().call_tool("search", {"query": "developer", "remote": True, "page": 2, "limit": 30})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "web-app-full-stack-engineer-niuro-remote-4461" and p["title"] == "Web App Full-Stack Engineer" and p["company"] == "Niuro"
    assert p["location"] == "Remote" and p["url"].endswith("-4461") and p["salary_min"] == 2500 and p["salary_max"] == 4000 and p["description"] == "<p>Build ...</p>"
    assert "posted_at" not in p and p["raw"]["attributes"]["published_at"] == 1790253211  # epoch integer stays raw
    assert sc["total"] is None and sc["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["query"] == "developer" and req.url.params["remote"] == "true" and req.url.params["page"] == "2" and req.url.params["per_page"] == "30"
    assert req.url.params["expand"] == '["company"]' and "country_code" not in req.url.params and "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_per_page_is_capped_at_the_documented_maximum_and_a_full_page_yields_next_page():
    respx.get(URL).mock(return_value=httpx.Response(200, json={"data": [HIT] * 120, "meta": {"page": 1, "per_page": 120, "total_pages": 3}}))
    res = await _server().call_tool("search", {"query": "rails", "limit": 100})
    assert res.is_error is False and len(res.structured_content["postings"]) == 120 and res.structured_content["next_page"] == 2
    assert respx.calls.last.request.url.params["per_page"] == "100"


@pytest.mark.asyncio
@respx.mock
async def test_unprocessable_search_is_an_invalid_input_result():
    respx.get(URL).mock(return_value=httpx.Response(422, json={"message": "unprocessable_content", "code": "unprocessable_content"}))
    res = await _server().call_tool("search", {"query": ""})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and res.structured_content["http_status"] == 422
