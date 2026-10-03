"""WhatsApp Cloud API: text send, mark as read, phone-number probe."""
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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "whatsapp.json").read_text(encoding="utf-8"))
G = "https://graph.facebook.com/v26.0"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "SYS-TOKEN", "phone_number_id": "106540352242922"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_webhook_only_reads_are_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["mark_read", "me", "send"]
    assert set(SPEC["adapter"]["not_offered"]) == {"list_inbound", "get_thread", "reply"}


@pytest.mark.asyncio
@respx.mock
async def test_send_text_message_documented_shape():
    route = respx.post(f"{G}/106540352242922/messages").mock(return_value=httpx.Response(200, json={
        "messaging_product": "whatsapp", "contacts": [{"input": "+16505551234", "wa_id": "16505551234"}], "messages": [{"id": "wamid.HBgLMTY0NjcwNDM1OTUVAgARGBI1RjQyNUE3NEYxMzAzMzQ5MkEA"}]}))
    res = await _server().call_tool("send", {"to": "+16505551234", "text": "hello"})
    assert res.is_error is False and res.structured_content["message_id"].startswith("wamid.") and res.structured_content["status"] == "sent"
    req = route.calls.last.request
    assert json.loads(req.content) == {"messaging_product": "whatsapp", "recipient_type": "individual", "to": "+16505551234", "type": "text", "text": {"body": "hello"}}
    assert req.headers["Authorization"] == "Bearer SYS-TOKEN"


@pytest.mark.asyncio
@respx.mock
async def test_mark_read_and_rate_limit():
    route = respx.post(f"{G}/106540352242922/messages").mock(return_value=httpx.Response(200, json={"success": True}))
    res = await _server().call_tool("mark_read", {"message_id": "wamid.X"})
    assert res.is_error is False and res.structured_content["status"] == "ok"
    assert json.loads(route.calls.last.request.content) == {"messaging_product": "whatsapp", "status": "read", "message_id": "wamid.X"}
    respx.get(f"{G}/106540352242922").mock(return_value=httpx.Response(429, headers={"Retry-After": "3"}, json={"error": {"code": 80007}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
