import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "elevenlabs.json").read_text(encoding="utf-8"))
CREDS = {'api_key': 'xi-secret'}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], CREDS, 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _q(req):
    return {k: v[0] for k, v in parse_qs(urlparse(str(req.url)).query).items()}


def _body(req):
    return json.loads(req.content)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {'delete_item', 'list_items', 'get_item', 'me'}


@pytest.mark.asyncio
@respx.mock
async def test_list_voices_cursor_and_header():
    route = respx.get("https://api.elevenlabs.io/v2/voices").mock(return_value=httpx.Response(200, json={
        "voices": [{"voice_id": "v1", "name": "Rachel", "preview_url": "https://cdn/p.mp3", "category": "premade"}], "has_more": True, "next_page_token": "tok2", "total_count": 40}))
    res = await _server().call_tool("list_items", {"query": "rach", "limit": 10, "cursor": "tok1"})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["xi-api-key"] == "xi-secret"
    assert _q(req) == {"page_size": "10", "next_page_token": "tok1", "search": "rach"}
    sc = res.structured_content
    assert (sc["items"][0]["id"], sc["items"][0]["title"], sc["next_cursor"], sc["total"]) == ("v1", "Rachel", "tok2", 40)


@pytest.mark.asyncio
@respx.mock
async def test_get_and_delete_voice():
    respx.get("https://api.elevenlabs.io/v1/voices/v1").mock(return_value=httpx.Response(200, json={"voice_id": "v1", "name": "Rachel", "description": "calm"}))
    route = respx.delete("https://api.elevenlabs.io/v1/voices/v1").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    res = await _server().call_tool("get_item", {"item_id": "v1"})
    assert (res.structured_content["id"], res.structured_content["content"]) == ("v1", "calm")
    res = await _server().call_tool("delete_item", {"item_id": "v1"})
    assert res.structured_content["status"] == "ok" and route.called


@pytest.mark.asyncio
@respx.mock
async def test_auth_error_scrubs_key():
    respx.get("https://api.elevenlabs.io/v1/user").mock(return_value=httpx.Response(401, json={"detail": {"status": "invalid_api_key", "message": "key xi-secret invalid"}}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "xi-secret" not in json.dumps(res.structured_content)
