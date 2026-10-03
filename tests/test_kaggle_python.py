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

SPEC = json.loads((ROOT / "catalog" / "competitions" / "kaggle.json").read_text(encoding="utf-8"))
BASE = "https://api.kaggle.com/v1/competitions.CompetitionApiService"

# ApiCompetition shape from kagglesdk 0.1.28 (competitions/types/competition_api_service.py)
COMP = {"id": 3136, "ref": "titanic", "title": "Titanic - Machine Learning from Disaster", "url": "https://www.kaggle.com/competitions/titanic",
        "category": "Getting Started", "reward": "Knowledge", "tags": [{"name": "tabular"}], "deadline": "2030-01-01T00:00:00Z",
        "enabledDate": "2012-09-28T21:13:33Z", "teamCount": 15000, "userHasEntered": False, "evaluationMetric": "Categorization Accuracy",
        "description": "Start here! Predict survival on the Titanic"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_token": "KGAT_secret_value"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["discover", "get_competition", "my_entries", "standings"]
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "enter", "submit"}


@pytest.mark.asyncio
@respx.mock
async def test_discover_posts_search_and_maps_competitions():
    route = respx.post(f"{BASE}/ListCompetitions").mock(return_value=httpx.Response(200, json={"competitions": [COMP], "nextPageToken": ""}))
    res = await _server().call_tool("discover", {"query": "titanic", "page": 2})
    assert res.is_error is False
    (c,) = res.structured_content["competitions"]
    assert c["id"] == "titanic" and c["kind"] == "Getting Started" and c["prize"] == "Knowledge" and c["starts_at"] == "2012-09-28T21:13:33Z"
    req = route.calls.last.request
    assert json.loads(req.content) == {"search": "titanic", "page": 2}
    assert req.headers["Authorization"] == "Bearer KGAT_secret_value"


@pytest.mark.asyncio
@respx.mock
async def test_standings_and_my_entries_send_the_competition_ref():
    lb = respx.post(f"{BASE}/GetLeaderboard").mock(return_value=httpx.Response(200, json={"submissions": [{"teamId": 7, "teamName": "Leaders", "submissionDate": "2026-09-20T00:00:00Z", "score": "0.99"}]}))
    res = await _server().call_tool("standings", {"competition_id": "titanic", "limit": 10})
    row = res.structured_content["standings"][0]
    assert row["team"] == "Leaders" and row["raw"]["score"] == "0.99"
    assert json.loads(lb.calls.last.request.content) == {"competitionName": "titanic", "pageSize": 10}
    respx.post(f"{BASE}/ListSubmissions").mock(return_value=httpx.Response(200, json={"submissions": [{"ref": 555, "date": "2026-09-21T10:00:00Z", "status": "COMPLETE", "publicScore": "0.77"}]}))
    res = await _server().call_tool("my_entries", {"competition_id": "titanic"})
    e = res.structured_content["entries"][0]
    assert e["id"] == "555" and e["status"] == "COMPLETE" and e["submitted_at"] == "2026-09-21T10:00:00Z"


@pytest.mark.asyncio
@respx.mock
async def test_auth_error_is_scrubbed():
    respx.post(f"{BASE}/GetCompetition").mock(return_value=httpx.Response(401, json={"code": 401, "message": "bad token KGAT_secret_value"}))
    res = await _server().call_tool("get_competition", {"competition_id": "titanic"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "KGAT_secret_value" not in json.dumps(res.structured_content)
