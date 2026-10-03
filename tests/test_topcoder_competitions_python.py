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

SPEC = json.loads((ROOT / "catalog" / "competitions" / "topcoder.json").read_text(encoding="utf-8"))

# https://api.topcoder.com/v6/challenges?status=Completed&perPage=1 (opened 2026-09-24), trimmed
CH = {"id": "6a5da7b6-3841-43cb-ae9d-98416bea0d9d", "name": "AI Deal Scoping Assistant", "description": "Sales teams...", "status": "COMPLETED",
      "track": {"id": "9b6fc876", "name": "Development", "track": "DEVELOPMENT"}, "tags": ["AI"], "startDate": "2026-09-01T12:00:00.000Z",
      "submissionEndDate": "2026-09-15T12:00:00.000Z", "prizeSets": [{"type": "PLACEMENT", "prizes": [{"type": "USD", "value": 2500}]}],
      "winners": [{"userId": 90396990, "handle": "jaypatel1325", "placement": 1}, {"userId": 22887344, "handle": "dileepa", "placement": 2}]}


def _server():
    return build_server(SPEC, transport=Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test"))


@pytest.mark.asyncio
async def test_public_tools_only():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["discover", "get_competition", "standings"]
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "my_entries", "enter", "submit"}


@pytest.mark.asyncio
@respx.mock
async def test_discover_maps_status_and_search():
    respx.get("https://api.topcoder.com/v6/challenges").mock(return_value=httpx.Response(200, json=[CH]))
    res = await _server().call_tool("discover", {"query": "ai", "status": "completed", "limit": 5})
    c = res.structured_content["competitions"][0]
    assert c["id"] == CH["id"] and c["title"] == "AI Deal Scoping Assistant" and c["kind"] == "Development" and c["tags"] == ["AI"]
    assert c["deadline"] == "2026-09-15T12:00:00.000Z" and res.structured_content["total"] is None
    q = respx.calls.last.request.url.params
    assert q["search"] == "ai" and q["status"] == "Completed" and q["perPage"] == "5" and q["page"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_upcoming_status_is_rejected_without_a_call():
    route = respx.get("https://api.topcoder.com/v6/challenges").mock(return_value=httpx.Response(200, json=[]))
    res = await _server().call_tool("discover", {"status": "upcoming"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and route.call_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_standings_are_the_winners():
    respx.get(f"https://api.topcoder.com/v6/challenges/{CH['id']}").mock(return_value=httpx.Response(200, json=CH))
    res = await _server().call_tool("standings", {"competition_id": CH["id"]})
    rows = res.structured_content["standings"]
    assert [(r["rank"], r["team"]) for r in rows] == [(1, "jaypatel1325"), (2, "dileepa")]
