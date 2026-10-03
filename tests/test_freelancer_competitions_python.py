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

SPEC = json.loads((ROOT / "catalog" / "competitions" / "freelancer.json").read_text(encoding="utf-8"))

# https://www.freelancer.com/api/contests/0.1/contests/active/?limit=2&query=logo (opened 2026-09-24), trimmed
CONTEST = {"id": 2790072, "owner_id": 45809580, "title": "Modern Navy & Orange Logo", "seo_url": "contest/Modern-Navy-Orange-Logo-2790072.html",
           "currency": {"code": "USD"}, "prize": 100.0, "description": "I'm re-branding my company", "status": "active", "type": "guaranteed", "time_ended": 1790337335}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "fl-token"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["discover", "get_competition", "me"]
    assert set(SPEC["adapter"]["not_offered"]) == {"standings", "my_entries", "enter", "submit"}


@pytest.mark.asyncio
@respx.mock
async def test_discover_searches_active_contests():
    respx.get("https://www.freelancer.com/api/contests/0.1/contests/active/").mock(return_value=httpx.Response(200, json={"status": "success", "result": {"contests": [CONTEST], "total_count": 105}}))
    res = await _server().call_tool("discover", {"query": "logo", "page": 2, "limit": 10})
    sc = res.structured_content
    c = sc["competitions"][0]
    assert c["id"] == "2790072" and c["kind"] == "guaranteed" and c["status"] == "active" and c["raw"]["prize"] == 100.0 and sc["total"] == 105
    req = respx.calls.last.request
    assert req.url.params["query"] == "logo" and req.url.params["offset"] == "10" and req.headers["freelancer-oauth-v1"] == "fl-token"


@pytest.mark.asyncio
@respx.mock
async def test_get_competition_unwraps_the_list_and_empty_is_invalid():
    respx.get("https://www.freelancer.com/api/contests/0.1/contests/2790072/").mock(return_value=httpx.Response(200, json={"status": "success", "result": {"contests": [CONTEST]}}))
    res = await _server().call_tool("get_competition", {"competition_id": "2790072"})
    assert res.structured_content["title"] == "Modern Navy & Orange Logo" and res.structured_content["description"].startswith("I'm")
    respx.get("https://www.freelancer.com/api/contests/0.1/contests/1/").mock(return_value=httpx.Response(200, json={"status": "success", "result": {"contests": [], "total_count": None}}))
    res = await _server().call_tool("get_competition", {"competition_id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
