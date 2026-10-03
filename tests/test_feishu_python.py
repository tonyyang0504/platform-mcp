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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "feishu.json").read_text(encoding="utf-8"))
F = "https://open.feishu.cn/open-apis"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"app_id": "cli_x", "app_secret": "sec", "receive_id_type": "chat_id"}, 50, "test", envelope=a["envelope"]))


def _login():
    return respx.post(f"{F}/auth/v3/tenant_access_token/internal").mock(return_value=httpx.Response(200, json={"code": 0, "msg": "ok", "tenant_access_token": "t-abc", "expire": 7200}))


@pytest.mark.asyncio
async def test_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "me", "reply", "send"]


@pytest.mark.asyncio
@respx.mock
async def test_send_and_reply_serialize_content_as_a_json_string():
    _login()
    route = respx.post(f"{F}/im/v1/messages").mock(return_value=httpx.Response(200, json={"code": 0, "msg": "success", "data": {"message_id": "om_9"}}))
    text = 'He said "hi"\nand left \\ ok'
    res = await _server().call_tool("send", {"to": "oc_1", "text": text})
    assert res.is_error is False and res.structured_content["message_id"] == "om_9"
    req = route.calls.last.request
    assert req.url.params["receive_id_type"] == "chat_id"
    body = json.loads(req.content)
    assert body["receive_id"] == "oc_1" and body["msg_type"] == "text" and isinstance(body["content"], str)
    assert json.loads(body["content"]) == {"text": text} and len(body["uuid"]) == 36
    rep = respx.post(f"{F}/im/v1/messages/om_1/reply").mock(return_value=httpx.Response(200, json={"code": 0, "data": {"message_id": "om_10"}}))
    res = await _server().call_tool("reply", {"thread_id": "om_1", "text": "ok"})
    assert res.structured_content["message_id"] == "om_10"
    assert json.loads(json.loads(rep.calls.last.request.content)["content"]) == {"text": "ok"}


@pytest.mark.asyncio
@respx.mock
async def test_tenant_token_login_then_bot_info():
    login = _login()
    respx.get(f"{F}/bot/v3/info").mock(return_value=httpx.Response(200, json={"code": 0, "bot": {"app_name": "name"}}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["account"]["bot"]["app_name"] == "name"
    assert json.loads(login.calls[0].request.content) == {"app_id": "cli_x", "app_secret": "sec"}
    assert respx.calls.last.request.headers["Authorization"] == "Bearer t-abc"


@pytest.mark.asyncio
@respx.mock
async def test_list_chat_and_thread_messages():
    _login()
    body = {"code": 0, "data": {"has_more": False, "items": [{"message_id": "om_1", "thread_id": "omt_1", "create_time": "1615380573411", "sender": {"id": "ou_1"}, "body": {"content": "{\"text\":\"hi\"}"}}]}}
    respx.get(f"{F}/im/v1/messages").mock(return_value=httpx.Response(200, json=body))
    res = await _server().call_tool("list_inbound", {"channel": "oc_1", "limit": 10})
    m = res.structured_content["messages"][0]
    assert m["id"] == "om_1" and m["from"] == "ou_1" and m["text"] == "{\"text\":\"hi\"}"
    q = respx.calls.last.request.url.params
    assert q["container_id_type"] == "chat" and q["container_id"] == "oc_1" and q["page_size"] == "10"
    res = await _server().call_tool("get_thread", {"thread_id": "omt_1"})
    q = respx.calls.last.request.url.params
    assert q["container_id_type"] == "thread" and q["container_id"] == "omt_1"


@pytest.mark.asyncio
@respx.mock
async def test_nonzero_code_is_an_is_error_result():
    _login()
    respx.get(f"{F}/im/v1/messages").mock(return_value=httpx.Response(200, json={"code": 230002, "msg": "Bot/User can NOT be out of the chat."}))
    res = await _server().call_tool("list_inbound", {"channel": "oc_x"})
    assert res.is_error is True and "out of the chat" in res.structured_content["message"]
