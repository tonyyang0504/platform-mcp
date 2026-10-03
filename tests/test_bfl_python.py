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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "bfl.json").read_text(encoding="utf-8"))
CREDS = {'api_key': 'bfl-key-secret', 'webhook_url': 'https://hooks.example.com/bfl'}


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
    assert {t.name for t in await _server().list_tools()} == {'generate_video', 'generate_image', 'me'}


@pytest.mark.asyncio
@respx.mock
async def test_generate_image_default_model_body_and_x_key():
    route = respx.post("https://api.bfl.ai/v1/flux-kontext-pro").mock(return_value=httpx.Response(200, json={"id": "t1", "polling_url": "https://api.us1.bfl.ai/v1/get_result?id=t1", "cost": 4}))
    res = await _server().call_tool("generate_image", {"prompt": "a red fox", "aspect_ratio": "16:9", "seed": 7, "image_url": "https://img.example.com/a.png"})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["x-key"] == "bfl-key-secret"
    assert _body(req) == {"prompt": "a red fox", "input_image": "https://img.example.com/a.png", "seed": 7, "aspect_ratio": "16:9", "webhook_url": "https://hooks.example.com/bfl"}
    assert res.structured_content["job_id"] == "t1" and res.structured_content["polling_url"].startswith("https://api.us1.bfl.ai/")


@pytest.mark.asyncio
@respx.mock
async def test_generate_image_model_in_path():
    route = respx.post("https://api.bfl.ai/v1/flux-2-pro").mock(return_value=httpx.Response(200, json={"id": "t2", "polling_url": "https://x/get_result?id=t2"}))
    res = await _server().call_tool("generate_image", {"prompt": "p", "model": "flux-2-pro"})
    assert res.is_error is False and route.called


@pytest.mark.asyncio
@respx.mock
async def test_generate_video_t2v_integer_duration():
    route = respx.post("https://api.bfl.ai/v1/flux-3-video").mock(return_value=httpx.Response(200, json={"id": "v1", "polling_url": "https://x/get_result?id=v1"}))
    res = await _server().call_tool("generate_video", {"prompt": "waves", "duration_seconds": 8, "aspect_ratio": "9:16"})
    assert res.is_error is False
    # auth audit: the Flux 3 video input schemas forbid extra properties and have no webhook_url
    assert _body(route.calls[0].request) == {"mode": "t2v", "prompt": "waves", "aspect_ratio": "9:16", "duration": 8}


@pytest.mark.asyncio
@respx.mock
async def test_me_credits_and_no_credits_error():
    respx.get("https://api.bfl.ai/v1/credits").mock(side_effect=[httpx.Response(200, json={"credits": 120.5}), httpx.Response(402, json={"detail": "insufficient credits"})])
    res = await _server().call_tool("me", {})
    assert res.structured_content == {"ok": True, "account": {"credits": 120.5}}
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
