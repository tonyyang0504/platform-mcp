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

SPEC = json.loads((ROOT / "catalog" / "social" / "devto.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "me", "read_comments"]  # no write verbs: v1 has no comment/delete endpoints
    rc = next(t for t in tools if t.name == "read_comments")
    assert rc.annotations.read_only_hint is True and rc.annotations.destructive_hint is False
    assert rc.input_schema["required"] == ["post_id"] and rc.output_schema["properties"]["comments"]["type"] == "array"
    assert rc.title == "Read comments"


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_maps_the_documented_comment_fields():
    # Forem API v1: GET /api/comments?a_id= -> [Comment{type_of, id_code, created_at, ...}] threaded via children
    respx.get("https://dev.to/api/comments").mock(return_value=httpx.Response(200, json=[
        {"type_of": "comment", "id_code": "abc1", "created_at": "2026-09-01T10:00:00Z", "body_html": "<p>nice</p>", "user": {"username": "jane"}, "children": []},
    ]))
    res = await _server().call_tool("read_comments", {"post_id": "321"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["comments"][0]["id"] == "abc1" and sc["comments"][0]["created_at"] == "2026-09-01T10:00:00Z"
    assert sc["comments"][0]["raw"]["user"]["username"] == "jane" and sc["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["a_id"] == "321" and req.url.params["per_page"] == "30" and req.url.params["page"] == "1"
    assert req.headers["api-key"] == "k"


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_an_auth_error_result():
    respx.get("https://dev.to/api/users/me").mock(return_value=httpx.Response(401, json={"error": "unauthorized"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
