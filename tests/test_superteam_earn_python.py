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

SPEC = json.loads((ROOT / "catalog" / "deals" / "superteam_earn.json").read_text(encoding="utf-8"))

# https://superteam.fun/api/listings (the documented earn.superteam.fun/api/listings/ redirects here; opened 2026-09-24)
FEED = [{
    "id": "766eb23d-2ffe-4fe9-8f2a-17f476ff7003", "rewardAmount": 5002, "deadline": "2026-09-30T22:59:59.000Z", "type": "bounty",
    "title": "Create a Short Video Explainer for Hisa: $5000 up for grabs.", "token": "USDG", "winnersAnnouncedAt": None,
    "slug": "create-a-short-video-explainer-for-hisa-dollar5000-up-for-grabs", "isWinnersAnnounced": False, "isFeatured": True, "compensationType": "fixed",
    "minRewardAsk": None, "maxRewardAsk": None, "agentAccess": "HUMAN_ONLY", "status": "OPEN", "isPro": False,
    "_count": {"Comments": 13, "Submission": 32}, "sponsor": {"name": "Hisa", "slug": "hisanigeria", "logo": "https://res.cloudinary.com/x.png", "isVerified": True},
}, {
    "id": "9c1e0b9a-0000-4000-8000-000000000001", "rewardAmount": None, "deadline": "2026-10-05T00:00:00.000Z", "type": "project",
    "title": "Build a Solana indexer", "token": "USDC", "slug": "build-a-solana-indexer", "compensationType": "range", "minRewardAsk": 2000, "maxRewardAsk": 4000,
    "agentAccess": "ALL", "status": "OPEN", "_count": {"Comments": 0, "Submission": 3}, "sponsor": {"name": "Example DAO", "slug": "example-dao"},
}]


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_discovery_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search_postings"]
    assert tools[0].meta["platform_mcp/endpoint"] == "/api/listings" and SPEC["adapter"]["base_url"] == "https://superteam.fun"
    assert "HUMAN_ONLY" in SPEC["adapter"]["not_offered"]["submit_bid"]


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_listings_and_keeps_agent_access_raw():
    respx.get("https://superteam.fun/api/listings").mock(return_value=httpx.Response(200, json=FEED))
    res = await _server().call_tool("search_postings", {"query": "video"})
    assert res.is_error is False
    bounty, project = res.structured_content["postings"]
    assert bounty["id"] == "766eb23d-2ffe-4fe9-8f2a-17f476ff7003" and bounty["buyer"] == "Hisa" and bounty["currency"] == "USDG" and bounty["deadline"] == "2026-09-30T22:59:59.000Z"
    assert bounty["budget_min"] is None and bounty["raw"]["rewardAmount"] == 5002 and bounty["raw"]["agentAccess"] == "HUMAN_ONLY"
    assert project["budget_min"] == 2000 and project["budget_max"] == 4000 and project["raw"]["slug"] == "build-a-solana-indexer"
    assert not respx.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_server_error_is_an_error_result():
    respx.get("https://superteam.fun/api/listings").mock(return_value=httpx.Response(500, json={"error": "Internal Server Error", "message": "Error occurred while fetching listings"}))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error" and res.structured_content["http_status"] == 500
