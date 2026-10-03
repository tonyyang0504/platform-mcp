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

SPEC = json.loads((ROOT / "catalog" / "social" / "wechat.json").read_text(encoding="utf-8"))
W = "https://api.weixin.qq.com/cgi-bin"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"appid": "wx123", "secret": "wechat-app-secret"}, 50, "test", envelope=a["envelope"]))


def _login():
    return respx.get(url__startswith=f"{W}/token").mock(return_value=httpx.Response(200, json={"access_token": "wxaccesstoken0001", "expires_in": 7200}))


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["delete", "me", "publish_text", "read_comments"]
    assert next(t for t in tools if t.name == "delete").annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_mass_sends_with_the_token_as_query_parameter():
    login = _login()
    route = respx.post(url__startswith=f"{W}/message/mass/sendall").mock(return_value=httpx.Response(200, json={"errcode": 0, "errmsg": "send job submission success", "msg_id": 34182}))
    res = await _server().call_tool("publish_text", {"text": "你好"})
    assert res.is_error is False and res.structured_content["id"] == "34182"
    p = login.calls.last.request.url.params
    assert p["grant_type"] == "client_credential" and p["appid"] == "wx123" and p["secret"] == "wechat-app-secret"
    req = route.calls.last.request
    assert req.url.params["access_token"] == "wxaccesstoken0001"
    assert json.loads(req.content) == {"filter": {"is_to_all": True}, "msgtype": "text", "text": {"content": "你好"}}


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_maps_the_comment_list():
    _login()
    route = respx.post(url__startswith=f"{W}/comment/list").mock(return_value=httpx.Response(200, json={
        "errcode": 0, "errmsg": "ok", "total": 1, "comment": [{"user_comment_id": 7, "openid": "oABC", "create_time": 1700000000, "content": "好文", "comment_type": 0}]}))
    res = await _server().call_tool("read_comments", {"post_id": "2247483650", "page": 2, "limit": 10})
    c = res.structured_content["comments"][0]
    assert c["id"] == "7" and c["author"] == "oABC" and c["text"] == "好文" and res.structured_content["total"] == 1
    assert json.loads(route.calls.last.request.content) == {"msg_data_id": 2247483650, "begin": 10, "count": 10, "type": 0}


@pytest.mark.asyncio
@respx.mock
async def test_errcode_is_an_error_without_leaking_secrets():
    _login()
    respx.post(url__startswith=f"{W}/message/mass/delete").mock(return_value=httpx.Response(200, json={"errcode": 40008, "errmsg": "invalid message type secret=wechat-app-secret"}))
    res = await _server().call_tool("delete", {"post_id": "30124"})
    assert res.is_error is True
    dumped = json.dumps(res.structured_content)
    assert "wechat-app-secret" not in dumped and "wxaccesstoken0001" not in dumped
