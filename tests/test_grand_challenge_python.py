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

SPEC = json.loads((ROOT / "catalog" / "competitions" / "grand_challenge.json").read_text(encoding="utf-8"))

# https://grand-challenge.org/api/v1/challenges/?limit=1 (opened 2026-09-24) and the Evaluation schema from /api/schema/
CH = {"api_url": "https://grand-challenge.org/api/v1/challenges/VESSEL12/", "url": "https://vessel12.grand-challenge.org/", "slug": "VESSEL12", "title": "",
      "description": "Segmentation of blood vessels in the lungs from CT images.", "public": True, "status": "CLOSED", "start_date": None, "end_date": None, "incentives": ["Publication"]}
EVAL = {"pk": "0e1b0c2a-0000-4000-8000-000000000001", "submission": {"pk": "s1", "phase": {"challenge": {"title": "", "short_name": "VESSEL12"}, "title": "Final", "slug": "final"},
        "creator": {"username": "alice"}}, "created": "2026-09-01T10:00:00Z", "published": True, "rank": 1, "rank_score": 0.93, "status": "Succeeded"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_token": "gc-token"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["discover", "get_competition", "me", "standings"]
    assert set(SPEC["adapter"]["not_offered"]) == {"my_entries", "enter", "submit"}


@pytest.mark.asyncio
@respx.mock
async def test_discover_uses_limit_offset_and_maps_slug():
    respx.get("https://grand-challenge.org/api/v1/challenges/").mock(return_value=httpx.Response(200, json={"count": 264, "next": "x", "previous": None, "results": [CH]}))
    res = await _server().call_tool("discover", {"page": 3, "limit": 1})
    sc = res.structured_content
    assert sc["competitions"][0]["id"] == "VESSEL12" and sc["competitions"][0]["status"] == "CLOSED" and sc["total"] == 264 and sc["next_page"] == 4
    q = respx.calls.last.request.url.params
    assert q["limit"] == "1" and q["offset"] == "2" and respx.calls.last.request.headers["Authorization"] == "Bearer gc-token"


@pytest.mark.asyncio
@respx.mock
async def test_standings_filter_evaluations_by_phase():
    respx.get("https://grand-challenge.org/api/v1/evaluations/").mock(return_value=httpx.Response(200, json={"count": 1, "next": None, "results": [EVAL]}))
    res = await _server().call_tool("standings", {"competition_id": "5c4b0c2a-0000-4000-8000-00000000abcd"})
    r = res.structured_content["standings"][0]
    assert r["rank"] == 1 and r["team"] == "alice" and r["score"] == 0.93
    assert respx.calls.last.request.url.params["submission__phase"] == "5c4b0c2a-0000-4000-8000-00000000abcd"


@pytest.mark.asyncio
@respx.mock
async def test_missing_challenge_is_not_found():
    respx.get("https://grand-challenge.org/api/v1/challenges/nope/").mock(return_value=httpx.Response(404, json={"detail": "Not found."}))
    res = await _server().call_tool("get_competition", {"competition_id": "nope"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
