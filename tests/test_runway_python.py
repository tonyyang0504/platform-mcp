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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "runway.json").read_text(encoding="utf-8"))
CREDS = {'api_key': 'rw-secret'}


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
    assert {t.name for t in await _server().list_tools()} == {'update_item', 'create_item', 'generate_video', 'me', 'get_job', 'list_items', 'generate_image', 'delete_item', 'get_item'}


B = "https://api.dev.runwayml.com/v1"


@pytest.mark.asyncio
@respx.mock
async def test_text_to_image_body_version_header():
    route = respx.post(f"{B}/text_to_image").mock(return_value=httpx.Response(200, json={"id": "11111111-1111-4111-8111-111111111111", "estimatedCost": {"credits": 5}}))
    res = await _server().call_tool("generate_image", {"prompt": "a lamp", "model": "gen4_image", "aspect_ratio": "1920:1080", "image_url": "https://x/ref.png"})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["X-Runway-Version"] == "2024-11-06" and req.headers["Authorization"] == "Bearer rw-secret"
    assert _body(req) == {"model": "gen4_image", "promptText": "a lamp", "ratio": "1920:1080", "referenceImages": [{"uri": "https://x/ref.png"}]}
    assert res.structured_content["job_id"].startswith("1111")


@pytest.mark.asyncio
@respx.mock
async def test_task_output_urls():
    respx.get(f"{B}/tasks/t1").mock(return_value=httpx.Response(200, json={"id": "t1", "status": "SUCCEEDED", "output": ["https://o/1.mp4"], "createdAt": "2026-09-25T00:00:00Z"}))
    res = await _server().call_tool("get_job", {"job_id": "t1"})
    assert res.structured_content["output_urls"] == ["https://o/1.mp4"] and res.structured_content["status"] == "SUCCEEDED"


@pytest.mark.asyncio
@respx.mock
async def test_documents_cursor_list_and_crud():
    lst = respx.get(f"{B}/documents").mock(return_value=httpx.Response(200, json={"data": [{"id": "d1", "name": "FAQ", "type": "text", "updatedAt": "2026-09-01"}], "hasMore": True, "nextCursor": "c2"}))
    res = await _server().call_tool("list_items", {"limit": 10, "cursor": "c1"})
    assert _q(lst.calls[0].request) == {"limit": "10", "cursor": "c1"}
    assert res.structured_content["next_cursor"] == "c2" and res.structured_content["items"][0]["title"] == "FAQ"
    cr = respx.post(f"{B}/documents").mock(return_value=httpx.Response(200, json={"id": "d2", "name": "Policy"}))
    res = await _server().call_tool("create_item", {"title": "Policy", "content": "# Returns"})
    assert _body(cr.calls[0].request) == {"name": "Policy", "content": "# Returns"} and res.structured_content["id"] == "d2"
    respx.delete(f"{B}/documents/d2").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("delete_item", {"item_id": "d2"})
    assert res.structured_content["status"] == "deleted"


@pytest.mark.asyncio
@respx.mock
async def test_throttle_429():
    respx.post(f"{B}/text_to_video").mock(return_value=httpx.Response(429, headers={"Retry-After": "5"}))
    res = await _server().call_tool("generate_video", {"prompt": "x", "model": "gen4.5", "aspect_ratio": "1280:720", "duration_seconds": 5})
    assert res.structured_content["error"] == "rate_limited"
