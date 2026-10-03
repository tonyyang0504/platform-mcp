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

SPEC = json.loads((ROOT / "catalog" / "competitions" / "codeforces.json").read_text(encoding="utf-8"))
BASE = "https://codeforces.com/api"
CONTESTS = {"status": "OK", "result": [
    {"id": 2261, "name": "Codeforces Round (Div. 1 + Div. 2)", "type": "CF", "phase": "BEFORE", "frozen": False, "durationSeconds": 10800, "startTimeSeconds": 1792247700},
    {"id": 2273, "name": "Codeforces Round (Div. 1)", "type": "CF", "phase": "BEFORE", "frozen": False, "durationSeconds": 9000, "startTimeSeconds": 1791743700},
    {"id": 566, "name": "VK Cup 2015 - Finals, online mirror", "type": "CF", "phase": "FINISHED", "frozen": False, "durationSeconds": 10800, "startTimeSeconds": 1438273200}]}
STANDINGS = {"status": "OK", "result": {
    "contest": {"id": 566, "name": "VK Cup 2015 - Finals, online mirror", "type": "CF", "phase": "FINISHED", "frozen": False, "durationSeconds": 10800, "startTimeSeconds": 1438273200},
    "problems": [], "rows": [
        {"party": {"contestId": 566, "members": [{"handle": "tourist"}], "participantType": "CONTESTANT"}, "rank": 1, "points": 3504.0, "penalty": 0, "problemResults": []},
        {"party": {"contestId": 566, "members": [{"handle": "a"}, {"handle": "b"}], "teamName": "Team AB", "participantType": "CONTESTANT"}, "rank": 2, "points": 3000.5, "penalty": 0, "problemResults": []},
        {"party": {"contestId": 566, "members": [{"handle": "c"}], "participantType": "CONTESTANT"}, "rank": 3, "points": 2100.0, "penalty": 0, "problemResults": []}]}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_public_reads_only():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["discover", "get_competition", "standings"]
    assert SPEC["adapter"]["rate_per_second"] <= 0.5  # "at most 1 time per two seconds"


@pytest.mark.asyncio
@respx.mock
async def test_discover_pages_the_full_list_locally():
    route = respx.get(f"{BASE}/contest.list").mock(return_value=httpx.Response(200, json=CONTESTS))
    s = (await _server().call_tool("discover", {"limit": 2})).structured_content
    assert [c["id"] for c in s["competitions"]] == ["2261", "2273"] and s["total"] == 3 and s["next_page"] == 2
    c = s["competitions"][0]
    assert c["url"] == "https://codeforces.com/contest/2261" and c["status"] == "BEFORE" and c["kind"] == "coding" and c["starts_at"] == "2026-10-17T14:35:00Z"
    assert route.calls.last.request.url.params["gym"] == "false"
    s2 = (await _server().call_tool("discover", {"limit": 2, "page": 2})).structured_content
    assert [c["id"] for c in s2["competitions"]] == ["566"] and s2["next_page"] is None


@pytest.mark.asyncio
@respx.mock
async def test_standings_send_only_contest_id_and_page_locally():
    route = respx.get(f"{BASE}/contest.standings").mock(return_value=httpx.Response(200, json=STANDINGS))
    s = (await _server().call_tool("standings", {"competition_id": "566", "limit": 2})).structured_content
    assert [(r["rank"], r["team"], r["score"]) for r in s["standings"]] == [(1, "tourist", 3504.0), (2, "Team AB", 3000.5)]
    assert s["next_page"] == 2 and s["total"] == 3
    assert dict(route.calls.last.request.url.params) == {"contestId": "566"}  # the API forbids from/count for anonymous callers
    g = (await _server().call_tool("get_competition", {"competition_id": "566"})).structured_content
    assert g["id"] == "566" and g["title"].startswith("VK Cup") and g["starts_at"] == "2015-07-30T16:20:00Z"


@pytest.mark.asyncio
@respx.mock
async def test_failed_envelope_and_http_400_are_tool_errors():
    respx.get(f"{BASE}/contest.list").mock(return_value=httpx.Response(200, json={"status": "FAILED", "comment": "Call limit exceeded"}))
    res = await _server().call_tool("discover", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
    respx.get(f"{BASE}/contest.standings").mock(return_value=httpx.Response(400, json={"status": "FAILED", "comment": "contestId: Contest with id 99999999 not found"}))
    res = await _server().call_tool("standings", {"competition_id": "99999999"})
    assert res.is_error is True and "not found" in res.structured_content["message"]


@pytest.mark.asyncio
@respx.mock
async def test_discover_filters_locally_by_title_kind_and_status():
    respx.get(f"{BASE}/contest.list").mock(return_value=httpx.Response(200, json=CONTESTS))
    s = _server()

    async def ids(args):
        return [c["id"] for c in (await s.call_tool("discover", args)).structured_content["competitions"]]
    assert await ids({"query": "div. 1"}) == ["2261", "2273"]
    assert await ids({"status": "completed"}) == ["566"]
    assert await ids({"status": "upcoming", "query": "div. 1 +"}) == ["2261"]
    assert await ids({"kind": "coding", "query": "vk cup"}) == ["566"] and await ids({"kind": "design"}) == []


@pytest.mark.asyncio
@respx.mock
async def test_competition_then_standings_pages_download_the_ranklist_once():
    route = respx.get(f"{BASE}/contest.standings").mock(return_value=httpx.Response(200, json=STANDINGS))
    s = _server()
    assert (await s.call_tool("get_competition", {"competition_id": "566"})).structured_content["title"] == "VK Cup 2015 - Finals, online mirror"
    p1 = (await s.call_tool("standings", {"competition_id": "566", "limit": 2})).structured_content
    p2 = (await s.call_tool("standings", {"competition_id": "566", "limit": 2, "page": 2})).structured_content
    assert [r["rank"] for r in p1["standings"]] == [1, 2] and [r["rank"] for r in p2["standings"]] == [3] and p1["next_page"] == 2
    assert route.call_count == 1  # ~14 MB for a large round: fetched once, paged from the 60 s cache


@pytest.mark.asyncio
@respx.mock
async def test_unknown_contest_400_is_not_found_and_extra_parameters_400_is_invalid_input():
    respx.get(f"{BASE}/contest.standings", params={"contestId": "99999999"}).mock(return_value=httpx.Response(400, json={"status": "FAILED", "comment": "contestId: Contest with id 99999999 not found"}))
    res = await _server().call_tool("get_competition", {"competition_id": "99999999"})
    assert res.is_error and res.structured_content["error"] == "not_found" and "99999999 not found" in res.structured_content["message"]
    respx.get(f"{BASE}/contest.standings", params={"contestId": "1"}).mock(return_value=httpx.Response(400, json={"status": "FAILED", "comment": "contestId: Non-gym contest standings for non-admin users are available only via anonymous GET requests with no extra parameters"}))
    res = await _server().call_tool("standings", {"competition_id": "1"})
    assert res.is_error and res.structured_content["error"] == "invalid_input"
