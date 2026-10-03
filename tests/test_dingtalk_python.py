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


SPEC = json.loads((ROOT / "catalog" / "messaging" / "dingtalk.json").read_text(encoding="utf-8"))
D = "https://api.dingtalk.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"app_key": "dingkey", "app_secret": "dingsec", "robot_code": "dingrobot"}, 50, "test"))


def _login():
    return respx.post(f"{D}/v1.0/oauth2/accessToken").mock(return_value=httpx.Response(200, json={"accessToken": "fw8ef", "expireIn": 7200}))


@pytest.mark.asyncio
async def test_only_send_is_served():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["send"]
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "list_inbound", "get_thread", "reply", "mark_read"}


@pytest.mark.asyncio
@respx.mock
async def test_login_then_batch_send_with_serialized_msg_param():
    login = _login()
    route = respx.post(f"{D}/v1.0/robot/oToMessages/batchSend").mock(return_value=httpx.Response(200, json={"processQueryKey": "zcxx", "invalidStaffIdList": []}))
    text = 'say "hi"\nbye'
    res = await _server().call_tool("send", {"to": "manager1234", "text": text})
    assert res.is_error is False and res.structured_content["message_id"] == "zcxx"
    assert json.loads(login.calls[0].request.content) == {"appKey": "dingkey", "appSecret": "dingsec"}
    req = route.calls.last.request
    assert req.headers["x-acs-dingtalk-access-token"] == "fw8ef" and "Authorization" not in req.headers
    body = json.loads(req.content)
    assert body["robotCode"] == "dingrobot" and body["userIds"] == ["manager1234"] and body["msgKey"] == "sampleText"
    assert json.loads(body["msgParam"]) == {"content": text}


@pytest.mark.asyncio
@respx.mock
async def test_invalid_msg_param_400_is_an_invalid_input():
    _login()
    respx.post(f"{D}/v1.0/robot/oToMessages/batchSend").mock(return_value=httpx.Response(400, json={"code": "invalidParameter.robotCode.notExsit", "message": "robot missing"}))
    res = await _server().call_tool("send", {"to": "u", "text": "x"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
