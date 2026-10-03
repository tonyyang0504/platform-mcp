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

SPEC = json.loads((ROOT / "catalog" / "social" / "google_business.json").read_text(encoding="utf-8"))
B = "https://mybusiness.googleapis.com/v4/accounts/111/locations/222"


def _server():
    a = SPEC["adapter"]
    creds = {"client_id": "c", "client_secret": "s", "refresh_token": "r", "account_id": "111", "location_id": "222", "language_code": "en-US"}
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds, 50, "test"))


def _token():
    return respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(200, json={"access_token": "ya29.B", "expires_in": 3599}))


@pytest.mark.asyncio
async def test_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["delete", "me", "publish_image", "publish_text", "read_mentions", "reply_comment"]


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_builds_a_standard_local_post():
    _token()
    route = respx.post(f"{B}/localPosts").mock(return_value=httpx.Response(200, json={"name": "accounts/111/locations/222/localPosts/9", "searchUrl": "https://g.page/x", "createTime": "2026-09-24T00:00:00Z"}))
    res = await _server().call_tool("publish_image", {"text": "Open late", "image_urls": ["https://img/1.jpg"]})
    assert res.is_error is False and res.structured_content["id"] == "accounts/111/locations/222/localPosts/9"
    assert json.loads(route.calls.last.request.content) == {"languageCode": "en-US", "summary": "Open late", "topicType": "STANDARD", "media": [{"mediaFormat": "PHOTO", "sourceUrl": "https://img/1.jpg"}]}


@pytest.mark.asyncio
@respx.mock
async def test_reviews_as_mentions_and_reply():
    _token()
    respx.get(f"{B}/reviews").mock(return_value=httpx.Response(200, json={"reviews": [{"reviewId": "r1", "reviewer": {"displayName": "Bo"}, "comment": "great", "createTime": "2026-09-01T00:00:00Z"}], "totalReviewCount": 1}))
    res = await _server().call_tool("read_mentions", {"limit": 10})
    assert res.structured_content["mentions"][0]["author"] == "Bo" and res.structured_content["total"] == 1
    route = respx.put(f"{B}/reviews/r1/reply").mock(return_value=httpx.Response(200, json={"comment": "thanks", "updateTime": "2026-09-24T00:00:00Z"}))
    res = await _server().call_tool("reply_comment", {"comment_id": "r1", "text": "thanks"})
    assert res.structured_content["created_at"] == "2026-09-24T00:00:00Z"
    assert json.loads(route.calls.last.request.content) == {"comment": "thanks"}


@pytest.mark.asyncio
@respx.mock
async def test_delete_and_expired_refresh_token_is_auth_error():
    _token()
    respx.delete(f"{B}/localPosts/9").mock(return_value=httpx.Response(200, json={}))
    res = await _server().call_tool("delete", {"post_id": "9"})
    assert res.structured_content["status"] == "deleted"
    respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
