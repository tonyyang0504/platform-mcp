"""Instagram messaging via the Messenger Platform (Facebook Login, Page token)."""
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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "instagram_dm.json").read_text(encoding="utf-8"))
G = "https://graph.facebook.com/v26.0"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"page_access_token": "PAGE-TOKEN", "page_id": "1234"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "me", "send"]
    assert set(SPEC["adapter"]["not_offered"]) == {"reply", "mark_read"}


@pytest.mark.asyncio
@respx.mock
async def test_send_addresses_the_igsid_without_messaging_type():
    route = respx.post(f"{G}/1234/messages").mock(return_value=httpx.Response(200, json={"recipient_id": "IGSID1", "message_id": "aWdfZAG"}))
    res = await _server().call_tool("send", {"to": "IGSID1", "text": "TEXT-OR-LINK"})
    assert res.is_error is False and res.structured_content["message_id"] == "aWdfZAG"
    assert json.loads(route.calls.last.request.content) == {"recipient": {"id": "IGSID1"}, "message": {"text": "TEXT-OR-LINK"}}


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_asks_for_instagram_conversations_and_maps_usernames():
    respx.get(f"{G}/1234/conversations").mock(return_value=httpx.Response(200, json={"data": [
        {"id": "c_1", "updated_time": "2022-07-12T19:11:07+0000", "messages": {"data": [{"id": "aWdGG", "message": "Hi Kitty!", "from": {"username": "fan", "id": "IGSID1"}, "created_time": "2022-07-12T19:11:07+0000"}]}}]}))
    res = await _server().call_tool("list_inbound", {"limit": 5})
    m = res.structured_content["messages"][0]
    assert m["from"] == "fan" and m["from_id"] == "IGSID1" and m["thread_id"] == "c_1" and m["text"] == "Hi Kitty!"
    params = respx.calls.last.request.url.params
    assert params["platform"] == "instagram" and params["limit"] == "5"
