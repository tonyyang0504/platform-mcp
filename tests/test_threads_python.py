"""Threads API: access_token query auth, one-call text publishing with auto_publish_text."""
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "social" / "threads.json").read_text(encoding="utf-8"))
T = "https://graph.threads.com/v1.0"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "TH-TOKEN"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_image_publishing_is_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "publish_text", "read_comments", "read_mentions", "reply_comment"]
    assert set(SPEC["adapter"]["not_offered"]) == {"publish_image"}


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_is_one_form_call_with_auto_publish():
    route = respx.post(f"{T}/me/threads").mock(return_value=httpx.Response(200, json={"id": "1234567"}))
    res = await _server().call_tool("publish_text", {"text": "hello threads", "reply_to": "999"})
    assert res.is_error is False and res.structured_content["id"] == "1234567"
    req = route.calls.last.request
    assert parse_qs(req.content.decode()) == {"media_type": ["TEXT"], "text": ["hello threads"], "reply_to_id": ["999"], "auto_publish_text": ["true"]}
    assert req.url.params["access_token"] == "TH-TOKEN"


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_maps_top_level_replies():
    respx.get(f"{T}/42/replies").mock(return_value=httpx.Response(200, json={"data": [
        {"id": "1234567890", "text": "First Reply", "username": "bob", "timestamp": "2024-01-01T18:20:00+0000"}], "paging": {"cursors": {"before": "B", "after": "A"}}}))
    res = await _server().call_tool("read_comments", {"post_id": "42"})
    c = res.structured_content["comments"][0]
    assert c["id"] == "1234567890" and c["author"] == "bob" and c["text"] == "First Reply"


@pytest.mark.asyncio
@respx.mock
async def test_insights_map_positionally_and_delete_answers_status():
    respx.get(f"{T}/42/insights").mock(return_value=httpx.Response(200, json={"data": [
        {"name": n, "period": "lifetime", "values": [{"value": v}], "id": f"42/insights/{n}/lifetime"}
        for n, v in [("likes", 100), ("replies", 10), ("reposts", 3), ("quotes", 1), ("views", 900), ("shares", 2)]]}))
    res = await _server().call_tool("analytics_post", {"post_id": "42"})
    sc = res.structured_content
    assert sc["likes"] == 100 and sc["replies"] == 10 and sc["views"] == 900 and sc["shares"] == 2 and sc["post_id"] == "42/insights/likes/lifetime"
    assert respx.calls.last.request.url.params["metric"] == "likes,replies,reposts,quotes,views,shares"
    respx.delete(f"{T}/42").mock(return_value=httpx.Response(200, json={"success": True, "deleted_id": "42"}))
    res = await _server().call_tool("delete", {"post_id": "42"})
    assert res.is_error is False and res.structured_content["status"] == "deleted"
