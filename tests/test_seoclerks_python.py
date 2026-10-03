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

SPEC = json.loads((ROOT / "catalog" / "deals" / "seoclerks.json").read_text(encoding="utf-8"))
URL = "https://www.seoclerks.com/api"

# job request as returned live on 2026-09-25 (type=inlinead&dt=wtb&oby=bidstart&f=json), trimmed
ROW = {"id": "105824", "title": "Looking for a Great gaming logo for Twitch and Youtube", "description": "i am looking for a great logo…",
       "service_url": "https://www.seoclerks.com/job/youtube/105824/Looking-for-a-Great-gaming-logo-for-Twitch-and-Youtube?utm_source=affiliate&utm_medium=API&utm_campaign=0",
       "price": "7", "days": "7", "create_date": "1789165346", "buyer_username": "gamerx"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered():
    assert [t.name for t in await _server().list_tools()] == ["search_postings"]


@pytest.mark.asyncio
@respx.mock
async def test_search_selects_job_requests_as_json():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=[ROW]))
    res = await _server().call_tool("search_postings", {"query": "logo", "category": "64", "limit": 10, "page": 3, "min_budget": 50})
    assert res.is_error is False
    assert dict(route.calls.last.request.url.params) == {"s": "logo", "c": "64", "am": "10", "type": "inlinead", "dt": "wtb", "oby": "bidstart", "f": "json"}
    p = res.structured_content["postings"][0]
    assert p["id"] == "105824" and p["buyer"] == "gamerx" and p["url"].startswith("https://www.seoclerks.com/job/") and p["raw"]["price"] == "7"


@pytest.mark.asyncio
@respx.mock
async def test_null_body_is_an_empty_list_and_limit_caps_at_40():
    route = respx.get(URL).mock(return_value=httpx.Response(200, text="null", headers={"Content-Type": "application/json"}))
    res = await _server().call_tool("search_postings", {"query": "zzzzqqq", "limit": 100})
    assert res.is_error is False and res.structured_content["postings"] == []
    assert route.calls.last.request.url.params["am"] == "40"


@pytest.mark.asyncio
@respx.mock
async def test_server_error_is_upstream_error():
    respx.get(URL).mock(return_value=httpx.Response(503, text="Service Unavailable"))
    res = await _server().call_tool("search_postings", {"query": "seo"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
