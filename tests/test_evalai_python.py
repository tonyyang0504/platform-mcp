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

SPEC = json.loads((ROOT / "catalog" / "competitions" / "evalai.json").read_text(encoding="utf-8"))

# https://eval.ai/api/challenges/challenge/present/approved/public and /api/jobs/challenge_phase_split/7035/leaderboard/ (opened 2026-09-24), trimmed
CHALLENGE = {"id": 2717, "title": "Dr.DocBench Challenge", "short_description": "Expert-level document parsing", "description": "<h2>Dr.DocBench</h2>",
             "submission_guidelines": "<p>Submit one .zip</p>", "start_date": "2026-08-10T00:00:00Z", "end_date": "2026-10-10T12:59:59Z",
             "domain_name": None, "list_tags": ["emnlp-2026", "document-parsing"], "is_registration_open": True}
ROW = {"id": 1304640, "submission__participant_team": 42337, "submission__participant_team__team_name": "PSK", "challenge_phase_split": 7035,
       "result": [0.1999, 62.26, 0.0, 80.62, 75.91], "submission__submitted_at": "2026-09-20T16:33:05.975816Z", "filtering_score": 75.91}


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"auth_token": "ev-token", "participant_team_id": "42337"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["discover", "enter", "get_competition", "me", "standings"]
    assert set(SPEC["adapter"]["not_offered"]) == {"my_entries", "submit"}


@pytest.mark.asyncio
@respx.mock
async def test_discover_lists_present_public_challenges():
    respx.get("https://eval.ai/api/challenges/challenge/present/approved/public").mock(return_value=httpx.Response(200, json={"count": 1, "next": None, "previous": None, "results": [CHALLENGE]}))
    res = await _server().call_tool("discover", {"query": "doc"})
    sc = res.structured_content
    c = sc["competitions"][0]
    assert c["id"] == "2717" and c["tags"] == ["emnlp-2026", "document-parsing"] and c["deadline"] == "2026-10-10T12:59:59Z"
    assert sc["total"] == 1 and sc["next_page"] is None
    req = respx.calls.last.request
    assert "query" not in req.url.params and req.headers["Authorization"] == "Bearer ev-token"


@pytest.mark.asyncio
@respx.mock
async def test_standings_read_the_phase_split_leaderboard():
    respx.get("https://eval.ai/api/jobs/challenge_phase_split/7035/leaderboard/").mock(return_value=httpx.Response(200, json={"count": 23, "next": None, "results": [ROW]}))
    res = await _server().call_tool("standings", {"competition_id": "7035"})
    r = res.structured_content["standings"][0]
    assert r["team"] == "PSK" and r["score"] == 75.91 and r["updated_at"] == "2026-09-20T16:33:05.975816Z" and res.structured_content["total"] == 23


@pytest.mark.asyncio
@respx.mock
async def test_enter_registers_the_configured_team():
    route = respx.post("https://eval.ai/api/challenges/challenge/2717/participant_team/42337").mock(return_value=httpx.Response(201))
    res = await _server().call_tool("enter", {"competition_id": "2717"})
    assert res.is_error is False and res.structured_content["id"] == "registered" and route.call_count == 1
    res = await _server({"auth_token": "ev-token"}).call_tool("enter", {"competition_id": "2717"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"  # no participant_team_id configured
