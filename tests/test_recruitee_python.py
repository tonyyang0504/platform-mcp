"""Recruitee Careers Site API: X-Careers-Sites-Token, published offers list, candidate-perspective apply."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "recruitee.json").read_text(encoding="utf-8"))
BASE = "https://recruiteedemo.recruitee.com/api"
TOKEN = "rc_careers_token_abc123"
OFFER = {"company_name": "Example company name", "title": "Example offer 1", "id": 1853589, "slug": "example-offer-1", "status": "published",
         "careers_url": "https://recruiteedemo.recruitee.com/o/example-offer-1", "published_at": "2026-09-26 10:46:21 UTC", "description": "Description text",
         "locations": [{"id": 171529, "name": "Example location 1", "city": "Amsterdam", "country_code": "NL"}],
         "salary": {"max": "1000", "min": "100", "period": "hour", "currency": "EUR"}}
CREDS = {"careers_token": TOKEN, "company_subdomain": "recruiteedemo", "applicant_name": "John Smith", "applicant_email": "john@example.com"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], CREDS, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_search_and_apply_with_honest_annotations():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["apply", "search"]
    assert tools["search"].annotations.read_only_hint is True and tools["apply"].annotations.read_only_hint is False
    assert "REAL application" in SPEC["adapter"]["tools"]["apply"]["note"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_the_careers_token_and_maps_slug_ids():
    respx.get(f"{BASE}/offers/").mock(return_value=httpx.Response(200, json={"offers": [OFFER]}))
    res = await _server().call_tool("search", {"query": "offer"})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "example-offer-1" and p["title"] == "Example offer 1" and p["company"] == "Example company name" and p["location"] == "Example location 1"
    assert p["url"].endswith("/o/example-offer-1") and p["raw"]["salary"]["currency"] == "EUR"
    req = respx.calls.last.request
    assert req.headers["X-Careers-Sites-Token"] == TOKEN and "Authorization" not in req.headers and not req.url.params


@pytest.mark.asyncio
@respx.mock
async def test_apply_posts_the_candidate_from_config_and_arguments():
    route = respx.post(f"{BASE}/offers/example-offer-1/candidates").mock(return_value=httpx.Response(201, json={"candidate": {"id": 7929046, "name": "John Smith"}}))
    res = await _server().call_tool("apply", {"id": "example-offer-1", "cover_letter": "Hello", "resume_url": "https://example.com/CV.pdf"})
    assert res.is_error is False and res.structured_content["application_id"] == "7929046" and res.structured_content["status"] == "submitted"
    body = json.loads(route.calls.last.request.content)
    assert body == {"candidate": {"name": "John Smith", "email": "john@example.com", "cover_letter": "Hello", "remote_cv_url": "https://example.com/CV.pdf"}}


@pytest.mark.asyncio
@respx.mock
async def test_refused_application_is_an_error_without_the_token():
    respx.post(f"{BASE}/offers/example-offer-1/candidates").mock(return_value=httpx.Response(422, json={"error": ["Phone can't be blank"], "token": TOKEN}))
    res = await _server().call_tool("apply", {"id": "example-offer-1"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
    assert TOKEN not in json.dumps(res.structured_content)
