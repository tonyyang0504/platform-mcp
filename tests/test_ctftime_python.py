"""CTFtime (forge stress test 2026-10): upcoming events paged locally, results keyed by event id ({competition_id} in
result.items), an HTML 404 page summarised by its title."""
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

SPEC = json.loads((ROOT / "catalog" / "competitions" / "ctftime.json").read_text(encoding="utf-8"))
BASE = "https://ctftime.org/api/v1"
EVENTS = [{"id": 3380, "title": "Hacker's Gambit 2026", "ctftime_url": "https://ctftime.org/event/3380/", "format": "Jeopardy", "start": "2026-10-02T06:30:00+00:00", "finish": "2026-10-04T06:30:00+00:00", "description": "qualifier"},
          {"id": 3390, "title": "AD Cup", "ctftime_url": "https://ctftime.org/event/3390/", "format": "Attack-Defense", "start": "2026-10-10T06:30:00+00:00", "finish": "2026-10-11T06:30:00+00:00", "description": ""}]


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_discover_and_standings():
    route = respx.get(f"{BASE}/events/").mock(return_value=httpx.Response(200, json=EVENTS))
    r = (await _server().call_tool("discover", {"kind": "Attack-Defense"})).structured_content
    assert [c["id"] for c in r["competitions"]] == ["3390"] and r["competitions"][0]["status"] == "upcoming"
    assert route.calls.last.request.url.params["limit"] == "100" and int(route.calls.last.request.url.params["start"]) > 1_700_000_000
    respx.get(f"{BASE}/results/").mock(return_value=httpx.Response(200, json={"3335": {"title": "Junior.Crypt", "scores": [
        {"team_id": 439893, "points": "12793.0000", "place": 1}, {"team_id": 431218, "points": "12274.5000", "place": 2}]}}))
    s = (await _server().call_tool("standings", {"competition_id": "3335", "limit": 1})).structured_content
    assert s["standings"][0] == {"rank": 1, "team": "439893", "score": 12793, "raw": {"team_id": 439893, "points": "12793.0000", "place": 1}} and s["next_page"] == 2
    assert (await _server().call_tool("standings", {"competition_id": "1"})).structured_content["standings"] == []


@pytest.mark.asyncio
@respx.mock
async def test_html_404_is_summarised():
    respx.get(f"{BASE}/events/99999999/").mock(return_value=httpx.Response(404, headers={"content-type": "text/html"},
        text="<!DOCTYPE html>\n<html lang=\"en\"><head><title>CTFtime.org / All about CTF / 404</title></head><body>...</body></html>"))
    r = await _server().call_tool("get_competition", {"competition_id": "99999999"})
    assert r.is_error and r.structured_content["message"] == "not found (404): HTML page: CTFtime.org / All about CTF / 404"
