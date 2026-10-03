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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "resend.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "re_k", "sender": "Acme <hello@acme.example>"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["list_inbound", "me", "send"]
    send = next(t for t in tools if t.name == "send")
    assert send.annotations.read_only_hint is False and send.input_schema["required"] == ["to", "text"]
    assert send.meta["platform_mcp/endpoint"] == "/emails"
    assert [f["name"] for f in SPEC["adapter"]["config_fields"]] == ["sender"]
    assert set(SPEC["adapter"]["not_offered"]) == {"reply", "get_thread", "mark_read"}


@pytest.mark.asyncio
@respx.mock
async def test_send_fills_from_with_the_sender_config_field():
    route = respx.post("https://api.resend.com/emails").mock(return_value=httpx.Response(200, json={"id": "49a3999c-0ce1-4ea6-ab68-afcd6dc2e794"}))
    res = await _server().call_tool("send", {"to": "bob@example.com", "subject": "Hello", "text": "hi"})
    assert res.is_error is False and res.structured_content["message_id"] == "49a3999c-0ce1-4ea6-ab68-afcd6dc2e794"
    body = json.loads(route.calls.last.request.content)
    assert body == {"from": "Acme <hello@acme.example>", "to": "bob@example.com", "subject": "Hello", "text": "hi"}
    assert route.calls.last.request.headers["Authorization"] == "Bearer re_k"


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_maps_received_emails():
    respx.get("https://api.resend.com/emails/receiving").mock(return_value=httpx.Response(200, json={
        "object": "list", "has_more": False,
        "data": [{"id": "a39999a6-88e3-48b1-888b-beaabcde1b33", "to": ["recipient@example.com"], "from": "sender@example.com", "created_at": "2026-10-09T14:37:40.951Z", "subject": "Hello World"}]}))
    res = await _server().call_tool("list_inbound", {"limit": 5})
    assert res.is_error is False
    m = res.structured_content["messages"][0]
    assert m["id"] == "a39999a6-88e3-48b1-888b-beaabcde1b33" and m["from"] == "sender@example.com" and m["to"] == "recipient@example.com" and m["sent_at"] == "2026-10-09T14:37:40.951Z"
    assert respx.calls.last.request.url.params["limit"] == "5"


@pytest.mark.asyncio
@respx.mock
async def test_validation_error_is_an_is_error_result():
    respx.post("https://api.resend.com/emails").mock(return_value=httpx.Response(422, json={"statusCode": 422, "name": "missing_required_field", "message": "Missing `subject` field."}))
    res = await _server().call_tool("send", {"to": "bob@example.com", "text": "hi"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and res.structured_content["http_status"] == 422
