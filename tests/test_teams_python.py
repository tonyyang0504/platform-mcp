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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "teams.json").read_text(encoding="utf-8"))
M = "https://graph.microsoft.com/v1.0"


def _server():
    a = SPEC["adapter"]
    creds = {"client_id": "app", "refresh_token": "0.AR", "team_id": "T1", "user_id": "U1", "tenant_id": "TN"}
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds, 50, "test"))


@pytest.fixture
def token():
    return respx.post("https://login.microsoftonline.com/common/oauth2/v2.0/token").mock(return_value=httpx.Response(200, json={"access_token": "eyJ.T", "expires_in": 3600}))


@pytest.mark.asyncio
async def test_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]


@pytest.mark.asyncio
@respx.mock
async def test_send_to_chat_without_client_secret(token):
    route = respx.post(f"{M}/chats/19:abc@thread.v2/messages").mock(return_value=httpx.Response(201, json={"id": "1616990032035", "body": {"content": "hi"}}))
    res = await _server().call_tool("send", {"to": "19:abc@thread.v2", "text": "hi"})
    assert res.structured_content["message_id"] == "1616990032035"
    assert json.loads(route.calls.last.request.content) == {"body": {"content": "hi"}}
    assert "client_secret" not in token.calls[0].request.content.decode()


@pytest.mark.asyncio
@respx.mock
async def test_channel_thread_replies_use_config_team(token):
    respx.get(url__startswith=f"{M}/teams/T1/channels/19:ch@thread.tacv2/messages/111/replies").mock(return_value=httpx.Response(200, json={"value": [
        {"id": "222", "replyToId": "111", "from": {"user": {"displayName": "Ann"}}, "body": {"content": "yo"}, "createdDateTime": "2026-09-24T00:00:00Z"}]}))
    res = await _server().call_tool("get_thread", {"thread_id": "111", "channel": "19:ch@thread.tacv2", "limit": 10})
    assert res.structured_content["messages"][0] == {**res.structured_content["messages"][0], "id": "222", "thread_id": "111", "from": "Ann"}
    reply = respx.post(f"{M}/teams/T1/channels/19:ch@thread.tacv2/messages/111/replies").mock(return_value=httpx.Response(201, json={"id": "333"}))
    res = await _server().call_tool("reply", {"thread_id": "111", "channel": "19:ch@thread.tacv2", "text": "ok"})
    assert res.structured_content["message_id"] == "333" and reply.called


@pytest.mark.asyncio
@respx.mock
async def test_mark_read_sends_user_identity(token):
    route = respx.post(f"{M}/chats/19:abc@thread.v2/markChatReadForUser").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("mark_read", {"channel": "19:abc@thread.v2"})
    assert res.structured_content["status"] == "read"
    assert json.loads(route.calls.last.request.content) == {"user": {"id": "U1", "tenantId": "TN"}}
