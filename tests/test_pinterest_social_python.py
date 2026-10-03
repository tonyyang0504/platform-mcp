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

SPEC = json.loads((ROOT / "catalog" / "social" / "pinterest.json").read_text(encoding="utf-8"))
P = "https://api.pinterest.com/v5"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"client_id": "1234", "client_secret": "sec", "refresh_token": "pinr.1", "board_id": "549755885175"}, 50, "test"))


def _token():
    return respx.post(f"{P}/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "pina.A", "expires_in": 2592000, "refresh_token": "pinr.2"}))


@pytest.mark.asyncio
async def test_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "publish_image"]


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_uses_image_url_source_and_basic_token_auth():
    tok = _token()
    route = respx.post(f"{P}/pins").mock(return_value=httpx.Response(201, json={"id": "813744226420795884", "created_at": "2026-09-24T00:00:00"}))
    res = await _server().call_tool("publish_image", {"text": "New drop", "image_urls": ["https://img/a.jpg", "https://img/b.jpg"]})
    assert res.is_error is False and res.structured_content["id"] == "813744226420795884"
    assert json.loads(route.calls.last.request.content) == {"board_id": "549755885175", "description": "New drop", "media_source": {"source_type": "image_url", "url": "https://img/a.jpg"}}
    assert tok.calls[0].request.headers["Authorization"].startswith("Basic ")


@pytest.mark.asyncio
@respx.mock
async def test_pin_metrics_and_delete():
    _token()
    respx.get(f"{P}/pins/81").mock(return_value=httpx.Response(200, json={"id": "81", "pin_metrics": {"90d": {"impression": 2}}}))
    res = await _server().call_tool("analytics_post", {"post_id": "81"})
    assert res.structured_content["metrics"] == {"90d": {"impression": 2}}
    assert respx.calls.last.request.url.params["pin_metrics"] == "true"
    respx.delete(f"{P}/pins/81").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("delete", {"post_id": "81"})
    assert res.structured_content["status"] == "deleted"
