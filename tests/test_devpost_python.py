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

SPEC = json.loads((ROOT / "catalog" / "deals" / "devpost.json").read_text(encoding="utf-8"))

# https://devpost.com/api/hackathons?status[]=open&page=1 (opened 2026-09-24)
PAGE = {
    "hackathons": [{
        "id": 29969, "title": "RevenueCat Shipaton 2026", "displayed_location": {"icon": "globe", "location": "Online"}, "open_state": "open",
        "thumbnail_url": "//d112y698adiu2z.cloudfront.net/photos/production/challenge_thumbnails/004/663/632/datas/medium_square.jpg",
        "url": "https://revenuecat-shipaton-2026.devpost.com/", "time_left_to_submission": "7 days left", "submission_period_dates": "Jul 31 - Oct 01, 2026",
        "themes": [{"id": 18, "name": "Design"}, {"id": 4, "name": "Gaming"}], "prize_amount": "$<span data-currency-value>740,000</span>", "prizes_counts": {"cash": 1, "other": 0},
        "registrations_count": 27362, "organization_name": "RevenueCat", "invite_only": False, "start_a_submission_url": "https://revenuecat-shipaton-2026.devpost.com/submissions/new",
    }],
    "meta": {"total_count": 50, "per_page": 9},
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_discovery_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search_postings"]
    assert tools[0].annotations.read_only_hint is True and tools[0].meta["platform_mcp/endpoint"] == "/api/hackathons"
    assert "submit_bid" in SPEC["adapter"]["not_offered"] and "get_posting" in SPEC["adapter"]["not_offered"]


@pytest.mark.asyncio
@respx.mock
async def test_search_pages_open_hackathons_with_the_site_page_size():
    respx.get("https://devpost.com/api/hackathons").mock(return_value=httpx.Response(200, json=PAGE))
    res = await _server().call_tool("search_postings", {"page": 2})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "29969" and p["title"] == "RevenueCat Shipaton 2026" and p["buyer"] == "RevenueCat" and p["url"] == "https://revenuecat-shipaton-2026.devpost.com/"
    assert p["deadline"] == "Jul 31 - Oct 01, 2026" and p["raw"]["registrations_count"] == 27362
    assert sc["total"] == 50 and sc["next_page"] is None  # one row < page size 9 -> no further page
    q = respx.calls.last.request.url.params
    assert q["page"] == "2" and q["status[]"] == "open" and "limit" not in q


@pytest.mark.asyncio
@respx.mock
async def test_bot_block_403_is_an_error_result():
    respx.get("https://devpost.com/api/hackathons").mock(return_value=httpx.Response(403, text="forbidden"))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403
