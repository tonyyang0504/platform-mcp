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

SPEC = json.loads((ROOT / "catalog" / "deals" / "remote_ok.json").read_text(encoding="utf-8"))

# https://remoteok.com/api (opened 2026-09-24): a bare array whose element 0 is the legal notice
FEED = [
    {"last_updated": 1790208007, "legal": "API Terms of Service: Please link back (with follow, and without nofollow!) to the URL on Remote OK and mention Remote OK as a source, so we get traffic back from your site. If you do not we'll have to suspend API access.\n\nPlease don't use the Remote OK logo without written permission as it's a registered trademark, please DO use our name Remote OK though."},
    {"slug": "remote-technical-product-manager-ai-stockbroking-app-bjak-1137421", "id": "1137421", "epoch": 1790121610, "date": "2026-09-23T00:00:10+00:00", "company": "Bjak ", "company_logo": "",
     "position": "Technical Product Manager AI Stockbroking App", "tags": ["product manager", "exec", "finance"], "description": "<p>About KIRA</p>", "location": "Worldwide",
     "apply_url": "https://remoteok.com/remote-jobs/remote-technical-product-manager-ai-stockbroking-app-bjak-1137421", "salary_min": 40000, "salary_max": 70000, "logo": "", "url": "https://remoteok.com/remote-jobs/remote-technical-product-manager-ai-stockbroking-app-bjak-1137421"},
]


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_the_feed_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search_postings"]
    sp = tools[0]
    assert sp.annotations.read_only_hint is True and sp.annotations.destructive_hint is False
    assert sp.title == "Search postings" and sp.meta["platform_mcp/endpoint"] == "/api"
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_posting", "submit_bid", "withdraw_bid", "bid_status", "list_messages", "send_message", "credits"}


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_the_feed_and_sends_no_parameters():
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=FEED))
    res = await _server().call_tool("search_postings", {"query": "python", "limit": 50})
    assert res.is_error is False
    sc = res.structured_content
    (job,) = sc["postings"]  # element 0 (the legal notice, id null) is dropped by `require: [id]`
    assert job["id"] == "1137421" and job["title"] == "Technical Product Manager AI Stockbroking App" and job["buyer"] == "Bjak "
    assert job["budget_min"] == 40000 and job["budget_max"] == 70000 and job["skills"] == ["product manager", "exec", "finance"]
    assert job["url"].endswith("-1137421") and job["posted_at"] == "2026-09-23T00:00:10+00:00"
    assert sc["total"] is None and sc["next_page"] is None
    req = respx.calls.last.request
    assert str(req.url) == "https://remoteok.com/api" and "Authorization" not in req.headers  # keyless, query is not sent


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(429, headers={"Retry-After": "5"}))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 5
