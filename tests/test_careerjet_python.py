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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "careerjet.json").read_text(encoding="utf-8"))
QUERY = "https://search.api.careerjet.net/v4/query"
URL = "https://jobview.careerjet.co.uk/python-developer-london-123.html?s=1234&t=1756721700"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "k", "user_ip": "203.0.113.9", "user_agent": "Mozilla/5.0 (X11)"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "search"]  # aggregator: no details, apply or messaging endpoints
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and "page 1-10" in search.description
    assert [f["name"] for f in SPEC["adapter"]["auth"]["fields"]] == ["api_key", "user_ip", "user_agent"]


@pytest.mark.asyncio
@respx.mock
async def test_search_carries_basic_auth_plus_end_user_context_and_maps_documented_fields():
    respx.get(QUERY).mock(return_value=httpx.Response(200, json={
        "type": "JOBS", "hits": 1, "pages": 1,
        "jobs": [{"title": "Python Developer", "company": "Acme Ltd", "locations": "London, UK", "salary": "£50,000 - £60,000",
                  "date": "2026-09-01T10:15:00Z", "url": URL, "description": "We are looking for a Python developer ..."}]}))
    res = await _server().call_tool("search", {"query": "python", "location": "London"})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == URL and p["url"] == URL and p["company"] == "Acme Ltd" and p["location"] == "London, UK" and p["posted_at"] == "2026-09-01T10:15:00Z"
    assert "salary_min" not in p and p["raw"]["salary"] == "£50,000 - £60,000"
    assert res.structured_content["total"] == 1 and res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["keywords"] == "python" and req.url.params["location"] == "London" and req.url.params["page"] == "1" and req.url.params["page_size"] == "25"
    assert req.url.params["user_ip"] == "203.0.113.9" and req.url.params["user_agent"] == "Mozilla/5.0 (X11)"
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"k:").decode()


@pytest.mark.asyncio
@respx.mock
async def test_missing_user_context_403_is_an_auth_error_result():
    respx.get(QUERY).mock(return_value=httpx.Response(403, json={"type": "ERROR", "error": "Missing param user_ip or user_agent"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403
    assert "Missing param user_ip" in res.structured_content["message"]
