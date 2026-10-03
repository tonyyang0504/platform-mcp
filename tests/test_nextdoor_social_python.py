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

SPEC = json.loads((ROOT / "catalog" / "social" / "nextdoor.json").read_text(encoding="utf-8"))
B = "https://nextdoor.com/external/api/partner/v1"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds or {"access_token": "nd-secret-token"}, 50, "test"))


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["delete", "me", "publish_image", "publish_text"]


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_creates_a_post_and_returns_the_share_link():
    route = respx.post(f"{B}/post/create/").mock(return_value=httpx.Response(200, json={"result": "success", "share_link": "https://nextdoor.com/p/abc123"}))
    res = await _server().call_tool("publish_text", {"text": "Lost cat on Elm St"})
    assert res.is_error is False and res.structured_content["id"] == "https://nextdoor.com/p/abc123"
    req = route.calls.last.request
    assert json.loads(req.content) == {"body_text": "Lost cat on Elm St"} and req.headers["Authorization"] == "Bearer nd-secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_sends_media_attachments_and_profile():
    route = respx.post(f"{B}/post/create/").mock(return_value=httpx.Response(200, json={"result": "success", "share_link": "https://nextdoor.com/p/x"}))
    await _server({"access_token": "nd-secret-token", "secure_profile_id": "biz9"}).call_tool("publish_image", {"text": "Open today", "image_urls": ["https://e.com/1.jpg", "https://e.com/2.jpg"]})
    assert json.loads(route.calls.last.request.content) == {"body_text": "Open today", "media_attachments": ["https://e.com/1.jpg", "https://e.com/2.jpg"], "secure_profile_id": "biz9"}


@pytest.mark.asyncio
@respx.mock
async def test_delete_and_auth_error_without_secret():
    route = respx.delete(url__startswith=f"{B}/post/").mock(return_value=httpx.Response(200, json={"message": "Post deleted successfully"}))
    res = await _server().call_tool("delete", {"post_id": "p1"})
    assert res.structured_content["status"] == "deleted" and route.calls.last.request.url.params["id"] == "p1"
    respx.get(f"{B}/me/").mock(return_value=httpx.Response(401, json={"detail": "invalid token nd-secret-token"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "nd-secret-token" not in json.dumps(res.structured_content)
