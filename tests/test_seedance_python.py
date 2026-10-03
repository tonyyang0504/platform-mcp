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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "seedance.json").read_text(encoding="utf-8"))
CREDS = {'api_key': 'ark-secret'}


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
    assert {t.name for t in await _server().list_tools()} == {'get_job', 'generate_video', 'generate_image', 'me'}


B = "https://ark.ap-southeast.bytepluses.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_video_task_content_array():
    route = respx.post(f"{B}/contents/generations/tasks").mock(return_value=httpx.Response(200, json={"id": "cgt-1"}))
    res = await _server().call_tool("generate_video", {"prompt": "kitten yawning", "model": "seedance-1-5-pro-251215", "aspect_ratio": "16:9", "duration_seconds": 5})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer ark-secret"
    assert _body(req) == {"model": "seedance-1-5-pro-251215", "content": [{"type": "text", "text": "kitten yawning"}], "ratio": "16:9", "duration": 5}
    assert res.structured_content["job_id"] == "cgt-1"


@pytest.mark.asyncio
@respx.mock
async def test_get_task_video_url():
    respx.get(f"{B}/contents/generations/tasks/cgt-1").mock(return_value=httpx.Response(200, json={"id": "cgt-1", "status": "succeeded", "content": {"video_url": "https://tos/v.mp4"}, "error": None}))
    res = await _server().call_tool("get_job", {"job_id": "cgt-1"})
    assert (res.structured_content["status"], res.structured_content["output_url"]) == ("succeeded", "https://tos/v.mp4")


@pytest.mark.asyncio
@respx.mock
async def test_image_sync_url_response_format():
    route = respx.post(f"{B}/images/generations").mock(return_value=httpx.Response(200, json={"model": "seedream", "data": [{"url": "https://i/1.png", "size": "2048x2048"}]}))
    res = await _server().call_tool("generate_image", {"prompt": "logo", "model": "seedream-4-0-250828", "size": "2K"})
    assert _body(route.calls[0].request) == {"model": "seedream-4-0-250828", "prompt": "logo", "size": "2K", "response_format": "url"}
    assert res.structured_content["output_url"] == "https://i/1.png"
