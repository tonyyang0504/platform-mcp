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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "supabase.json").read_text(encoding="utf-8"))
CREDS = {'secret_key': 'sb_secret_abc', 'project_ref': 'abcd1234'}


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
    assert {t.name for t in await _server().list_tools()} == {'update_item', 'create_item', 'delete_item', 'list_items', 'get_item'}


B = "https://abcd1234.supabase.co/rest/v1"


@pytest.mark.asyncio
@respx.mock
async def test_list_rows_offset_and_apikey_header():
    route = respx.get(f"{B}/todos").mock(return_value=httpx.Response(200, json=[{"id": 1, "title": "a"}, {"id": 2, "title": "b"}]))
    res = await _server().call_tool("list_items", {"collection": "todos", "page": 2, "limit": 2})
    req = route.calls[0].request
    assert req.headers["apikey"] == "sb_secret_abc" and "Authorization" not in req.headers
    assert _q(req) == {"limit": "2", "offset": "2", "select": "*"}
    assert [i["id"] for i in res.structured_content["items"]] == ["1", "2"] and res.structured_content["next_page"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_get_row_eq_filter():
    route = respx.get(f"{B}/todos").mock(return_value=httpx.Response(200, json=[{"id": 7, "title": "x"}]))
    res = await _server().call_tool("get_item", {"collection": "todos", "item_id": "7"})
    assert _q(route.calls[0].request) == {"id": "eq.7", "select": "*"}
    assert res.structured_content["title"] == "x"
    route.mock(return_value=httpx.Response(200, json=[]))
    res = await _server().call_tool("get_item", {"collection": "todos", "item_id": "8"})
    assert res.structured_content["error"] == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_insert_and_upsert_array_bodies():
    route = respx.post(f"{B}/todos").mock(return_value=httpx.Response(201, json=[{"id": 9, "title": "new"}]))
    res = await _server().call_tool("create_item", {"collection": "todos", "fields": {"title": "new", "done": False}})
    req = route.calls[0].request
    assert _body(req) == [{"title": "new", "done": False}] and req.headers["Prefer"] == "return=representation"
    assert res.structured_content["id"] == "9"
    await _server().call_tool("update_item", {"collection": "todos", "item_id": "9", "fields": {"done": True}})
    req = route.calls[1].request
    assert _body(req) == [{"done": True, "id": "9"}] and req.headers["Prefer"].startswith("resolution=merge-duplicates")


@pytest.mark.asyncio
@respx.mock
async def test_delete_row_204():
    route = respx.delete(f"{B}/todos").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("delete_item", {"collection": "todos", "item_id": "9"})
    assert _q(route.calls[0].request) == {"id": "eq.9"} and res.structured_content["status"] == "deleted"
