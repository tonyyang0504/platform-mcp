"""OpenLigaDB (forge stress test 2026-10, OpenAPI 3.0.4 in German, no servers listed): league list paged locally,
a league table by 'shortcut/season'."""
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

SPEC = json.loads((ROOT / "catalog" / "competitions" / "openligadb.json").read_text(encoding="utf-8"))
BASE = "https://api.openligadb.de"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_leagues_and_table():
    respx.get(f"{BASE}/getavailableleagues").mock(return_value=httpx.Response(200, json=[
        {"leagueId": 4821, "leagueName": "1. Fußball-Bundesliga 2025/2026", "leagueShortcut": "bl1", "leagueSeason": "2025", "sport": {"sportName": "Fußball"}},
        {"leagueId": 4822, "leagueName": "2. Fußball-Bundesliga 2025/2026", "leagueShortcut": "bl2", "leagueSeason": "2025", "sport": {"sportName": "Fußball"}},
        {"leagueId": 900, "leagueName": "Handball-Bundesliga", "leagueShortcut": "hbl", "leagueSeason": "2025", "sport": {"sportName": "Handball"}}]))
    r = (await _server().call_tool("discover", {"query": "fußball-bundesliga", "limit": 1})).structured_content
    assert [c["id"] for c in r["competitions"]] == ["bl1/2025"] and r["total"] == 2 and r["next_page"] == 2
    route = respx.get(f"{BASE}/getbltable/bl1/2025").mock(return_value=httpx.Response(200, json=[
        {"teamName": "FC Bayern München", "points": 89, "matches": 34}, {"teamName": "Borussia Dortmund", "points": 70, "matches": 34}]))
    s = (await _server().call_tool("standings", {"competition_id": "bl1/2025"})).structured_content["standings"]
    assert [(x["team"], x["score"], x["entries"]) for x in s] == [("FC Bayern München", 89, 34), ("Borussia Dortmund", 70, 34)] and route.called
