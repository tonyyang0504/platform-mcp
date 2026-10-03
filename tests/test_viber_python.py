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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "viber.json").read_text(encoding="utf-8"))
V = "https://chatapi.viber.com/pa"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"auth_token": "445da6az1s345z78", "sender_name": "Shop"}, 50, "test", envelope=a["envelope"]))


@pytest.mark.asyncio
async def test_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "send"]


@pytest.mark.asyncio
@respx.mock
async def test_send_text_with_sender_name_and_token_header():
    route = respx.post(f"{V}/send_message").mock(return_value=httpx.Response(200, json={"status": 0, "status_message": "ok", "message_token": 5741311803571721087}))
    res = await _server().call_tool("send", {"to": "01234567890A=", "text": "Hello"})
    assert res.is_error is False and res.structured_content == {**res.structured_content, "message_id": "5741311803571721087", "status": "sent"}
    assert json.loads(route.calls.last.request.content) == {"receiver": "01234567890A=", "type": "text", "text": "Hello", "sender": {"name": "Shop"}}
    assert route.calls.last.request.headers["X-Viber-Auth-Token"] == "445da6az1s345z78"


@pytest.mark.asyncio
@respx.mock
async def test_account_info_and_in_body_failure_status():
    respx.post(f"{V}/get_account_info").mock(return_value=httpx.Response(200, json={"status": 0, "status_message": "ok", "id": "pa:1", "name": "Shop"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["account"]["name"] == "Shop"
    respx.post(f"{V}/send_message").mock(return_value=httpx.Response(200, json={"status": 6, "status_message": "notSubscribed"}))
    res = await _server().call_tool("send", {"to": "x", "text": "y"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
    assert "notSubscribed" in res.structured_content["message"]
