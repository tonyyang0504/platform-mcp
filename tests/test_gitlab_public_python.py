"""GitLab.com public projects (forge stress test 2026-10, OpenAPI 2.0 YAML): keyset pagination whose next page exists
only in the Link response header (result.next_cursor link:id_after)."""
import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.adapter import from_headers, parse_link_header  # noqa: E402
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "gitlab_public.json").read_text(encoding="utf-8"))
URL = "https://gitlab.com/api/v4/projects"
LINK = '<https://gitlab.com/api/v4/projects?id_after=89655&order_by=id&pagination=keyset&per_page=2&search=mcp&sort=asc>; rel="next"'


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


def test_link_header_parsing():
    links = parse_link_header('<https://x/?page=3>; rel="next", <https://x/?page=1>; rel="prev first", <https://x/?page=9>; rel=last')
    assert links == {"next": "https://x/?page=3", "prev": "https://x/?page=1", "first": "https://x/?page=1", "last": "https://x/?page=9"}
    assert from_headers("link:page", {"link": '<https://x/?page=3>; rel="next"'}) == "3"
    assert from_headers("link:page", {}) is None and from_headers("header:X-Total", {"x-total": "42"}) == "42"


@pytest.mark.asyncio
@respx.mock
async def test_keyset_cursor_from_link_header():
    route = respx.get(URL).mock(side_effect=[
        httpx.Response(200, headers={"link": LINK}, json=[{"id": 22269, "path_with_namespace": "a/mcp1", "web_url": "https://gitlab.com/a/mcp1"},
                                                          {"id": 89655, "path_with_namespace": "b/mcp2", "web_url": "https://gitlab.com/b/mcp2"}]),
        httpx.Response(200, json=[{"id": 90000, "path_with_namespace": "c/mcp3", "web_url": "https://gitlab.com/c/mcp3"}])])
    p1 = (await _server().call_tool("list_items", {"query": "mcp", "limit": 2})).structured_content
    assert [i["id"] for i in p1["items"]] == ["22269", "89655"] and p1["next_cursor"] == "89655" and p1["next_page"] is None
    q = route.calls.last.request.url.params
    assert (q["pagination"], q["order_by"], q["per_page"]) == ("keyset", "id", "2") and "id_after" not in q
    p2 = (await _server().call_tool("list_items", {"query": "mcp", "limit": 2, "cursor": "89655"})).structured_content
    assert [i["id"] for i in p2["items"]] == ["90000"] and p2["next_cursor"] is None
    assert route.calls.last.request.url.params["id_after"] == "89655"
