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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "huggingface.json").read_text(encoding="utf-8"))
CREDS = {'token': 'hf_secret'}


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
    assert {t.name for t in await _server().list_tools()} == {'update_item', 'create_item', 'me', 'list_items', 'get_item'}


@pytest.mark.asyncio
@respx.mock
async def test_list_datasets_with_search():
    route = respx.get("https://huggingface.co/api/datasets").mock(return_value=httpx.Response(200, json=[{"id": "org/ds", "lastModified": "2026-09-01T00:00:00.000Z", "downloads": 5}]))
    res = await _server().call_tool("list_items", {"collection": "datasets", "query": "squad", "limit": 5})
    assert res.is_error is False
    assert route.calls[0].request.headers["Authorization"] == "Bearer hf_secret"
    assert _q(route.calls[0].request) == {"search": "squad", "limit": "5"}
    assert res.structured_content["items"][0]["id"] == "org/ds"


@pytest.mark.asyncio
@respx.mock
async def test_get_model_default_collection_keeps_slash():
    route = respx.get("https://huggingface.co/api/models/google/gemma-2b").mock(return_value=httpx.Response(200, json={"id": "google/gemma-2b", "lastModified": "2026-01-01"}))
    res = await _server().call_tool("get_item", {"item_id": "google/gemma-2b"})
    assert res.structured_content["id"] == "google/gemma-2b" and route.called


@pytest.mark.asyncio
@respx.mock
async def test_create_space_repo_body():
    route = respx.post("https://huggingface.co/api/repos/create").mock(return_value=httpx.Response(200, json={"url": "https://huggingface.co/spaces/me/demo", "name": "me/demo", "id": "0123456789abcdef01234567"}))
    res = await _server().call_tool("create_item", {"collection": "spaces", "title": "demo", "fields": {"private": True, "sdk": "gradio"}})
    assert res.is_error is False
    assert _body(route.calls[0].request) == {"type": "space", "name": "demo", "private": True, "sdk": "gradio"}
    assert (res.structured_content["id"], res.structured_content["url"]) == ("me/demo", "https://huggingface.co/spaces/me/demo")


@pytest.mark.asyncio
@respx.mock
async def test_update_settings_and_bad_collection():
    route = respx.put("https://huggingface.co/api/models/me/m1/settings").mock(return_value=httpx.Response(200, json={"private": False, "gated": "auto"}))
    res = await _server().call_tool("update_item", {"item_id": "me/m1", "fields": {"private": False, "gated": "auto"}})
    assert res.structured_content["status"] == "updated"
    assert _body(route.calls[0].request) == {"private": False, "gated": "auto"}
    res = await _server().call_tool("create_item", {"collection": "papers", "title": "x"})
    assert res.structured_content["error"] == "invalid_input"
