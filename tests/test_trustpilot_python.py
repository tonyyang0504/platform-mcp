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

SPEC = json.loads((ROOT / "catalog" / "social" / "trustpilot.json").read_text(encoding="utf-8"))
T = "https://api.trustpilot.com/v1"
TOKEN_URL = "https://api.trustpilot.com/v1/oauth/oauth-business-users-for-applications/refresh"


def _server():
    a = SPEC["adapter"]
    creds = {"client_id": "key", "client_secret": "sec", "refresh_token": "RT", "business_unit_id": "507f", "business_user_id": "u9"}
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds, 50, "test"))


def _token():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "AT", "refresh_token": "RT2", "expires_in": "359999"}))


@pytest.mark.asyncio
async def test_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "read_mentions", "reply_comment"]


@pytest.mark.asyncio
@respx.mock
async def test_reviews_as_mentions_with_basic_refresh():
    tok = _token()
    respx.get(f"{T}/private/business-units/507f/reviews").mock(return_value=httpx.Response(200, json={"reviews": [
        {"id": "r1", "text": "Great", "createdAt": "2026-09-01T00:00:00Z", "consumer": {"displayName": "John"}, "stars": 5}]}))
    res = await _server().call_tool("read_mentions", {"page": 2, "limit": 10})
    m = res.structured_content["mentions"][0]
    assert m["id"] == "r1" and m["author"] == "John" and m["text"] == "Great"
    q = respx.calls.last.request.url.params
    assert q["page"] == "2" and q["perPage"] == "10" and q["orderBy"] == "createdat.desc"
    assert tok.calls[0].request.headers["Authorization"].startswith("Basic ")


@pytest.mark.asyncio
@respx.mock
async def test_reply_to_review():
    _token()
    route = respx.post(f"{T}/private/reviews/r1/reply").mock(return_value=httpx.Response(201))
    res = await _server().call_tool("reply_comment", {"comment_id": "r1", "text": "Thank you"})
    assert res.is_error is False and res.structured_content["id"] == "reply"
    assert json.loads(route.calls.last.request.content) == {"authorBusinessUserId": "u9", "message": "Thank you"}
    assert route.calls.last.request.headers["Authorization"] == "Bearer AT"
