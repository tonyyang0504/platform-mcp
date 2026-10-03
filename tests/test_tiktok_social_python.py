import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "social" / "tiktok.json").read_text(encoding="utf-8"))
CREDS = {"client_key": "awCLIENTKEY01", "client_secret": "TT-SECRET-0123", "refresh_token": "rft.one-abc", "privacy_level": "SELF_ONLY"}
TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test", envelope=a.get("envelope")))


def _token_ok(access="act.minted-1", refresh="rft.two-def"):
    return respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": access, "expires_in": 86400, "open_id": "o1", "refresh_token": refresh, "refresh_expires_in": 31536000, "token_type": "Bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_sends_client_key_and_rotates():
    tok = _token_ok()
    me = respx.get(url__startswith="https://open.tiktokapis.com/v2/user/info/").mock(return_value=httpx.Response(200, json={"data": {"user": {"open_id": "o1", "display_name": "Ann"}}, "error": {"code": "ok"}}))
    creds = dict(CREDS)
    s = _server(creds)
    res = await s.call_tool("me", {})
    assert res.is_error is False
    form = parse_qs(tok.calls[0].request.content.decode())
    assert form == {"client_key": ["awCLIENTKEY01"], "client_secret": ["TT-SECRET-0123"], "grant_type": ["refresh_token"], "refresh_token": ["rft.one-abc"]}
    assert "client_id" not in form
    req = me.calls[0].request
    assert req.headers["Authorization"] == "Bearer act.minted-1" and req.url.params["fields"] == "open_id,union_id,avatar_url,display_name"


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_direct_posts_photos_from_urls():
    _token_ok()
    route = respx.post("https://open.tiktokapis.com/v2/post/publish/content/init/").mock(return_value=httpx.Response(200, json={"data": {"publish_id": "p_pub_url~v2.123"}, "error": {"code": "ok", "message": ""}}))
    res = await _server().call_tool("publish_image", {"text": "cats #fyp", "image_urls": ["https://cdn.example.com/a.webp", "https://cdn.example.com/b.webp"]})
    assert res.is_error is False and res.structured_content["id"] == "p_pub_url~v2.123"
    body = json.loads(route.calls[0].request.content)
    assert body == {"media_type": "PHOTO", "post_mode": "DIRECT_POST", "post_info": {"description": "cats #fyp", "privacy_level": "SELF_ONLY"},
                    "source_info": {"source": "PULL_FROM_URL", "photo_images": ["https://cdn.example.com/a.webp", "https://cdn.example.com/b.webp"], "photo_cover_index": 0}}


@pytest.mark.asyncio
@respx.mock
async def test_analytics_post_queries_one_video():
    _token_ok()
    route = respx.post(url__startswith="https://open.tiktokapis.com/v2/video/query/").mock(return_value=httpx.Response(200, json={"data": {"videos": [{"id": "7077642457847991554", "like_count": 12, "view_count": 340, "comment_count": 2, "share_count": 1}]}, "error": {"code": "ok"}}))
    res = await _server().call_tool("analytics_post", {"post_id": "7077642457847991554"})
    assert res.structured_content["post_id"] == "7077642457847991554" and res.structured_content["metrics"]["view_count"] == 340
    assert json.loads(route.calls[0].request.content) == {"filters": {"video_ids": ["7077642457847991554"]}}
    assert "like_count" in route.calls[0].request.url.params["fields"]


@pytest.mark.asyncio
@respx.mock
async def test_refused_refresh_is_an_auth_error_without_secrets():
    respx.post(TOKEN).mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "refresh token rft.one-abc expired", "log_id": "x"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "rft.one-abc" not in json.dumps(res.structured_content) and "TT-SECRET-0123" not in json.dumps(res.structured_content)
