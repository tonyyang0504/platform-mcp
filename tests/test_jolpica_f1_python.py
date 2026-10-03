"""Jolpica F1 (forge stress test 2026-10, Markdown docs): limit/offset paging whose MRData.total is a JSON string,
ids built from two fields ('season/round') and used as a path value with a slash."""
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

SPEC = json.loads((ROOT / "catalog" / "competitions" / "jolpica_f1.json").read_text(encoding="utf-8"))
BASE = "https://api.jolpi.ca/ergast/f1"
RACE = {"season": "2026", "round": "5", "url": "https://en.wikipedia.org/wiki/2026_Canadian_Grand_Prix", "raceName": "Canadian Grand Prix", "date": "2026-05-24", "time": "20:00:00Z",
        "Circuit": {"circuitName": "Circuit Gilles Villeneuve", "Location": {"locality": "Montreal", "country": "Canada"}}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_races_paging_with_string_total():
    route = respx.get(f"{BASE}/current/races.json").mock(return_value=httpx.Response(200, json={"MRData": {"limit": "2", "offset": "2", "total": "23", "RaceTable": {"Races": [RACE, {**RACE, "round": "6"}]}}}))
    r = (await _server().call_tool("discover", {"limit": 2, "page": 2})).structured_content
    assert [c["id"] for c in r["competitions"]] == ["2026/5", "2026/6"] and r["total"] == 23 and r["next_page"] == 3
    assert (route.calls.last.request.url.params["limit"], route.calls.last.request.url.params["offset"]) == ("2", "2")


@pytest.mark.asyncio
@respx.mock
async def test_race_detail_and_results():
    respx.get(f"{BASE}/2026/5/races.json").mock(return_value=httpx.Response(200, json={"MRData": {"total": "1", "RaceTable": {"Races": [RACE]}}}))
    c = (await _server().call_tool("get_competition", {"competition_id": "2026/5"})).structured_content
    assert (c["id"], c["starts_at"], c["description"]) == ("2026/5", "2026-05-24T20:00:00Z", "Circuit Gilles Villeneuve, Montreal, Canada")
    respx.get(f"{BASE}/2026/5/results.json").mock(return_value=httpx.Response(200, json={"MRData": {"total": "22", "RaceTable": {"Races": [{**RACE, "Results": [
        {"position": "1", "points": "25", "Driver": {"givenName": "Andrea Kimi", "familyName": "Antonelli"}, "Constructor": {"name": "Mercedes"}}]}]}}}))
    s = (await _server().call_tool("standings", {"competition_id": "2026/5", "limit": 1})).structured_content
    assert s["standings"][0]["team"] == "Andrea Kimi Antonelli (Mercedes)" and s["standings"][0]["rank"] == 1 and s["total"] == 22
    respx.get(f"{BASE}/2026/99/races.json").mock(return_value=httpx.Response(200, json={"MRData": {"total": "0", "RaceTable": {"Races": []}}}))
    r = await _server().call_tool("get_competition", {"competition_id": "2026/99"})
    assert r.is_error and r.structured_content["error"] == "not_found"
