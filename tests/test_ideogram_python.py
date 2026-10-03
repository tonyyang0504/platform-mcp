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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "ideogram.json").read_text(encoding="utf-8"))
CREDS = {'api_key': 'ideo-secret'}


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
    assert {t.name for t in await _server().list_tools()} == {'me', 'get_job', 'list_items', 'get_item', 'generate_image'}


@pytest.mark.asyncio
@respx.mock
async def test_generate_legacy_json_body_and_api_key_header():
    route = respx.post("https://api.ideogram.ai/generate").mock(return_value=httpx.Response(200, json={"created": "2026-09-25T00:00:00Z", "data": [{"url": "https://ideogram.ai/api/images/ephemeral/x.png", "seed": 3, "prompt": "cat", "resolution": "1024x1024", "is_image_safe": True}]}))
    res = await _server().call_tool("generate_image", {"prompt": "cat", "aspect_ratio": "ASPECT_16_9", "model": "V_2", "seed": 3, "negative_prompt": "dog"})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["Api-Key"] == "ideo-secret"
    assert _body(req) == {"image_request": {"prompt": "cat", "negative_prompt": "dog", "aspect_ratio": "ASPECT_16_9", "model": "V_2", "seed": 3}}
    assert res.structured_content["output_url"].endswith("x.png") and res.structured_content["status"] == "completed"


@pytest.mark.asyncio
@respx.mock
async def test_poll_generation():
    respx.get("https://api.ideogram.ai/v1/generations/g1").mock(return_value=httpx.Response(200, json={"generation_id": "g1", "status": "completed", "data": [{"url": "https://i/1.png"}]}))
    res = await _server().call_tool("get_job", {"job_id": "g1"})
    assert (res.structured_content["job_id"], res.structured_content["status"], res.structured_content["output_url"]) == ("g1", "completed", "https://i/1.png")


@pytest.mark.asyncio
@respx.mock
async def test_list_and_get_models():
    respx.get("https://api.ideogram.ai/models").mock(return_value=httpx.Response(200, json={"models": [{"model_id": "m1", "name": "Brand", "status": "COMPLETED", "creation_time": "2026-01-01"}]}))
    respx.get("https://api.ideogram.ai/models/m1").mock(return_value=httpx.Response(200, json={"model": {"model_id": "m1", "name": "Brand"}}))
    res = await _server().call_tool("list_items", {})
    assert res.structured_content["items"][0]["title"] == "Brand"
    res = await _server().call_tool("get_item", {"item_id": "m1"})
    assert res.structured_content["id"] == "m1"
