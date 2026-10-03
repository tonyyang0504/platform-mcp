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

import base64

SPEC = json.loads((ROOT / "catalog" / "messaging" / "zendesk.json").read_text(encoding="utf-8"))
Z = "https://acme.zendesk.com/api/v2"


def _server():
    a = SPEC["adapter"]
    creds = {"email_token": "jdoe@example.com/token", "api_token": "6wiIBWbG", "subdomain": "acme"}
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds, 50, "test"))


@pytest.mark.asyncio
async def test_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "me", "reply", "send"]


@pytest.mark.asyncio
@respx.mock
async def test_basic_email_token_auth_on_subdomain():
    respx.get(f"{Z}/users/me").mock(return_value=httpx.Response(200, json={"user": {"id": 1, "email": "jdoe@example.com"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False
    expected = "Basic " + base64.b64encode(b"jdoe@example.com/token:6wiIBWbG").decode()
    assert respx.calls.last.request.headers["Authorization"] == expected


@pytest.mark.asyncio
@respx.mock
async def test_list_tickets_and_comments():
    respx.get(f"{Z}/tickets").mock(return_value=httpx.Response(200, json={"tickets": [{"id": 35436, "requester_id": 20978392, "description": "fire", "updated_at": "2026-09-24T00:00:00Z"}], "count": 1}))
    res = await _server().call_tool("list_inbound", {"page": 2, "limit": 10})
    assert res.structured_content["messages"][0]["thread_id"] == "35436" and res.structured_content["total"] == 1
    q = respx.calls.last.request.url.params
    assert q["page"] == "2" and q["per_page"] == "10" and q["sort_order"] == "desc"
    respx.get(f"{Z}/tickets/35436/comments").mock(return_value=httpx.Response(200, json={"comments": [{"id": 5, "author_id": 7, "plain_body": "help", "created_at": "2026-09-24T00:00:00Z"}], "count": 1}))
    res = await _server().call_tool("get_thread", {"thread_id": "35436"})
    assert res.structured_content["messages"][0]["text"] == "help"


@pytest.mark.asyncio
@respx.mock
async def test_send_creates_ticket_and_reply_adds_public_comment():
    create = respx.post(f"{Z}/tickets").mock(return_value=httpx.Response(201, json={"ticket": {"id": 99}, "audit": {"id": 1}}))
    res = await _server().call_tool("send", {"to": "cust@example.com", "text": "Hello", "subject": "Your order"})
    assert res.structured_content["message_id"] == "99"
    assert json.loads(create.calls.last.request.content) == {"ticket": {"subject": "Your order", "comment": {"body": "Hello"}, "requester": {"email": "cust@example.com"}}}
    upd = respx.put(f"{Z}/tickets/99").mock(return_value=httpx.Response(200, json={"ticket": {"id": 99}, "audit": {"id": 555}}))
    res = await _server().call_tool("reply", {"thread_id": "99", "text": "Done"})
    assert res.structured_content["message_id"] == "555"
    assert json.loads(upd.calls.last.request.content) == {"ticket": {"comment": {"body": "Done", "public": True}}}
