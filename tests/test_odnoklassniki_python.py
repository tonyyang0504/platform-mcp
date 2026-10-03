import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, parse_qsl, urlsplit

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "social" / "odnoklassniki.json").read_text(encoding="utf-8"))
CREDS = {"application_key": "CBAKEYOK123", "application_secret_key": "OKSECRET-0123456789", "access_token": "tkn-ok-abcdef0123", "group_id": "53038939046008"}
URL = "https://api.ok.ru/fb.do"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check(request):
    q = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = q.pop("sig")
    assert "access_token" not in q and CREDS["application_secret_key"] not in str(request.url)
    ssk = hashlib.md5((CREDS["access_token"] + CREDS["application_secret_key"]).encode()).hexdigest()
    assert sig == hashlib.md5(("".join(f"{k}={q[k]}" for k in sorted(q)) + ssk).encode()).hexdigest()
    assert parse_qs(request.content.decode())["access_token"] == [CREDS["access_token"]]
    return q


@pytest.mark.asyncio
@respx.mock
async def test_me_is_signed_with_the_session_secret_key():
    route = respx.post(url__startswith=URL).mock(return_value=httpx.Response(200, json={"uid": "574829", "name": "Ann Lee"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["uid"] == "574829"
    q = _check(route.calls.last.request)
    assert q == {"method": "users.getCurrentUser", "application_key": "CBAKEYOK123", "format": "json"}


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_posts_a_group_theme():
    route = respx.post(url__startswith=URL).mock(return_value=httpx.Response(200, json="155013581046904"))
    res = await _server().call_tool("publish_text", {"text": "Привет, мир"})
    assert res.is_error is False and res.structured_content["status"] == "published"
    q = _check(route.calls.last.request)
    assert q["method"] == "mediatopic.post" and q["gid"] == "53038939046008" and q["type"] == "GROUP_THEME"
    assert json.loads(q["attachment"]) == {"media": [{"type": "text", "text": "Привет, мир"}]}


@pytest.mark.asyncio
@respx.mock
async def test_comments_with_anchor_and_topic_stats():
    def handler(request):
        q = dict(parse_qsl(urlsplit(str(request.url)).query))
        if q["method"] == "discussions.getComments":
            assert q["discussionId"] == "155013581046904" and q["discussionType"] == "GROUP_TOPIC" and q["count"] == "10"
            return httpx.Response(200, json={"anchor": "ANCH-2", "comments": [{"id": "c1", "author_id": "9", "author_name": "Bob", "text": "hi", "date": "2026-09-25 10:00:00"}]})
        return httpx.Response(200, json={"topic": {"id": "155013581046904", "reach": 120, "likes": 7, "comments": 1}})
    respx.post(url__startswith=URL).mock(side_effect=handler)
    s = _server()
    c = await s.call_tool("read_comments", {"post_id": "155013581046904", "limit": 10})
    assert c.structured_content["comments"][0]["text"] == "hi" and c.structured_content["next_cursor"] == "ANCH-2"
    a = await s.call_tool("analytics_post", {"post_id": "155013581046904"})
    assert a.structured_content["post_id"] == "155013581046904" and a.structured_content["metrics"]["reach"] == 120


@pytest.mark.asyncio
@respx.mock
async def test_error_code_body_is_an_error_without_secrets():
    respx.post(url__startswith=URL).mock(return_value=httpx.Response(200, json={"error_code": 102, "error_msg": "PARAM_SESSION_EXPIRED : Session expired tkn-ok-abcdef0123", "error_data": None}))
    res = await _server().call_tool("delete", {"post_id": "1"})
    assert res.is_error is True
    assert CREDS["access_token"] not in json.dumps(res.structured_content)
