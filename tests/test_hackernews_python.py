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

SPEC = json.loads((ROOT / "catalog" / "social" / "hackernews.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_are_read_only_and_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "me"]  # HN has no write API
    ap = next(t for t in tools if t.name == "analytics_post")
    assert ap.annotations.read_only_hint is True and ap.annotations.destructive_hint is False
    assert ap.input_schema["required"] == ["post_id"] and ap.meta["platform_mcp/endpoint"] == "/item/{post_id}.json"


@pytest.mark.asyncio
@respx.mock
async def test_analytics_post_maps_score_and_descendants_from_the_item():
    # https://github.com/HackerNews/API item example
    respx.get("https://hacker-news.firebaseio.com/v0/item/8863.json").mock(return_value=httpx.Response(200, json={
        "by": "dhouston", "descendants": 71, "id": 8863, "kids": [8952, 9224], "score": 111, "time": 1175714200,
        "title": "My YC app: Dropbox - Throw away your USB drive", "type": "story", "url": "http://www.getdropbox.com/u/2/screencast.html"}))
    res = await _server().call_tool("analytics_post", {"post_id": "8863"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["post_id"] == "8863" and sc["score"] == 111 and sc["comments"] == 71 and sc["author"] == "dhouston" and sc["raw"]["kids"] == [8952, 9224]
    assert "Authorization" not in respx.calls.last.request.headers  # unauthenticated API


@pytest.mark.asyncio
@respx.mock
async def test_network_failure_is_a_tool_error_not_a_protocol_error():
    respx.get("https://hacker-news.firebaseio.com/v0/item/1.json").mock(side_effect=httpx.ConnectError("boom"))
    res = await _server().call_tool("analytics_post", {"post_id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error" and "ConnectError" in res.structured_content["message"]
