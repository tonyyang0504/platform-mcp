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


SPEC = json.loads((ROOT / "catalog" / "messaging" / "wecom.json").read_text(encoding="utf-8"))
W = "https://qyapi.weixin.qq.com/cgi-bin"


def _server():
    a = SPEC["adapter"]
    creds = {"corpid": "ww1", "corpsecret": "csec", "agent_id": "1000002"}
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds, 50, "test", envelope=a["envelope"]))


def _login():
    return respx.get(url__startswith=f"{W}/gettoken").mock(return_value=httpx.Response(200, json={"errcode": 0, "errmsg": "ok", "access_token": "accesstoken000001", "expires_in": 7200}))


@pytest.mark.asyncio
async def test_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "send"]


@pytest.mark.asyncio
@respx.mock
async def test_get_login_and_token_as_query_parameter():
    login = _login()
    respx.get(url__startswith=f"{W}/agent/get").mock(return_value=httpx.Response(200, json={"errcode": 0, "errmsg": "ok", "agentid": 1000002, "name": "Bot"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["name"] == "Bot"
    lq = login.calls[0].request.url.params
    assert lq["corpid"] == "ww1" and lq["corpsecret"] == "csec"
    req = respx.calls.last.request
    assert req.url.params["access_token"] == "accesstoken000001" and req.url.params["agentid"] == "1000002"
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_send_text_with_integer_agentid():
    _login()
    route = respx.post(url__startswith=f"{W}/message/send").mock(return_value=httpx.Response(200, json={"errcode": 0, "errmsg": "ok", "invaliduser": "", "msgid": "xx1"}))
    res = await _server().call_tool("send", {"to": "UserID1|UserID2", "text": "快递到了"})
    assert res.structured_content["message_id"] == "xx1"
    assert json.loads(route.calls.last.request.content) == {"touser": "UserID1|UserID2", "msgtype": "text", "agentid": 1000002, "text": {"content": "快递到了"}}
    assert route.calls.last.request.url.params["access_token"] == "accesstoken000001"


@pytest.mark.asyncio
@respx.mock
async def test_errcode_in_http_200_is_an_is_error_result():
    _login()
    respx.post(url__startswith=f"{W}/message/send").mock(return_value=httpx.Response(200, json={"errcode": 42001, "errmsg": "access_token expired"}))
    res = await _server().call_tool("send", {"to": "u", "text": "x"})
    assert res.is_error is True and "expired" in res.structured_content["message"]
