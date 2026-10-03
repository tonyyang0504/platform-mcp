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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "kling.json").read_text(encoding="utf-8"))
CREDS = {'api_key': 'kling-secret'}


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


B = "https://api-singapore.klingai.com"


@pytest.mark.asyncio
@respx.mock
async def test_generate_video_settings_body_and_bearer():
    route = respx.post(f"{B}/text-to-video/kling-3.0").mock(return_value=httpx.Response(200, json={"code": 0, "message": "SUCCEED", "request_id": "r", "data": {"id": "t9", "status": "submitted"}}))
    res = await _server().call_tool("generate_video", {"prompt": "a train", "aspect_ratio": "9:16", "duration_seconds": 10})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer kling-secret"
    assert _body(req) == {"prompt": "a train", "settings": {"aspect_ratio": "9:16", "duration": 10}}
    assert (res.structured_content["job_id"], res.structured_content["status"]) == ("t9", "submitted")


@pytest.mark.asyncio
@respx.mock
async def test_get_job_unified_task_query():
    route = respx.get(f"{B}/tasks").mock(return_value=httpx.Response(200, json={"code": 0, "data": [{"id": "t9", "status": "succeeded", "outputs": [{"type": "video", "url": "https://v/1.mp4"}]}]}))
    res = await _server().call_tool("get_job", {"job_id": "t9"})
    assert _q(route.calls[0].request) == {"task_ids": "t9"}
    assert (res.structured_content["status"], res.structured_content["output_url"]) == ("succeeded", "https://v/1.mp4")


@pytest.mark.asyncio
@respx.mock
async def test_generate_image_and_envelope_error():
    route = respx.post(f"{B}/v1/images/generations").mock(side_effect=[
        httpx.Response(200, json={"code": 0, "data": {"task_id": "i1", "task_status": "submitted"}}),
        httpx.Response(200, json={"code": 1301, "message": "prompt rejected by risk control", "data": None})])
    res = await _server().call_tool("generate_image", {"prompt": "puppy", "model": "kling-v3", "image_url": "https://x/dog.png"})
    assert _body(route.calls[0].request) == {"model_name": "kling-v3", "prompt": "puppy", "image": "https://x/dog.png"}
    assert res.structured_content["job_id"] == "i1"
    res = await _server().call_tool("generate_image", {"prompt": "bad"})
    assert res.is_error is True and "risk control" in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_me_costs_window_in_epoch_ms():
    route = respx.get(f"{B}/account/costs").mock(return_value=httpx.Response(200, json={"code": 0, "data": {"resource_pack_subscribe_infos": []}}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["ok"] is True
    q = _q(route.calls[0].request)
    assert int(q["end_time"]) - int(q["start_time"]) >= 29 * 86400 * 1000 and len(q["end_time"]) == 13
