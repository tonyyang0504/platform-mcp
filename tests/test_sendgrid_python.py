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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "sendgrid.json").read_text(encoding="utf-8"))


def _server():
    # `sender` is the non-secret per-install config field used as from.email
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "SG.secret-key", "sender": "sender@example.com"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "send"]
    send = next(t for t in tools if t.name == "send")
    assert send.annotations.read_only_hint is False and send.annotations.destructive_hint is False
    assert send.input_schema["required"] == ["to", "text"] and send.title == "Send a message"
    assert send.meta["platform_mcp/endpoint"] == "/mail/send"
    assert set(SPEC["adapter"]["not_offered"]) == {"list_inbound", "get_thread", "reply", "mark_read"}


@pytest.mark.asyncio
@respx.mock
async def test_send_builds_the_personalizations_and_content_arrays_with_a_bearer_key():
    # docs: POST /v3/mail/send answers 202 Accepted with an empty body
    route = respx.post("https://api.sendgrid.com/v3/mail/send").mock(return_value=httpx.Response(202, headers={"X-Message-Id": "W0H2aKW7QIeoGqmmQ7bzXQ"}))
    res = await _server().call_tool("send", {"to": "receiver@example.com", "subject": "Hello", "text": "hi there", "channel": "ignored"})
    assert res.is_error is False and res.structured_content["status"] == "accepted"
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "personalizations": [{"to": [{"email": "receiver@example.com"}]}],
        "from": {"email": "sender@example.com"},
        "subject": "Hello",
        "content": [{"type": "text/plain", "value": "hi there"}],
    }
    assert route.calls.last.request.headers["Authorization"] == "Bearer SG.secret-key"


@pytest.mark.asyncio
@respx.mock
async def test_me_reads_the_user_account():
    respx.get("https://api.sendgrid.com/v3/user/account").mock(return_value=httpx.Response(200, json={"reputation": 100, "type": "paid"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True and res.structured_content["account"] == {"reputation": 100, "type": "paid"}


@pytest.mark.asyncio
@respx.mock
async def test_validation_and_auth_failures_are_error_results_without_the_key():
    respx.post("https://api.sendgrid.com/v3/mail/send").mock(return_value=httpx.Response(400, json={"errors": [{"message": "The subject is required. You can get around this requirement if you use a template with a subject defined or if every personalization has a subject defined.", "field": "subject"}]}))
    res = await _server().call_tool("send", {"to": "receiver@example.com", "text": "hi"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "subject" in res.structured_content["message"]
    respx.get("https://api.sendgrid.com/v3/user/account").mock(return_value=httpx.Response(401, json={"errors": [{"message": "The provided authorization grant is invalid, expired, or revoked", "field": None, "help": None}]}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "SG.secret-key" not in json.dumps(res.structured_content)
