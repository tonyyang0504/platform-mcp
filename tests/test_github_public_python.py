"""GitHub public search (forge stress test 2026-10, 13 MB OpenAPI): collection mapped into the path, owner/repo ids
with a slash kept, 403 'API rate limit exceeded' reported as rate_limited (not auth_error)."""
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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "github_public.json").read_text(encoding="utf-8"))
BASE = "https://api.github.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_search_and_get_repository():
    route = respx.get(f"{BASE}/search/repositories").mock(return_value=httpx.Response(200, json={"total_count": 3, "incomplete_results": False, "items": [
        {"full_name": "modelcontextprotocol/servers", "html_url": "https://github.com/modelcontextprotocol/servers", "updated_at": "2026-10-01T13:09:21Z"},
        {"full_name": "a/b", "html_url": "https://github.com/a/b", "updated_at": "2026-09-01T00:00:00Z"}]}))
    r = (await _server().call_tool("list_items", {"collection": "repositories", "query": "mcp server", "limit": 2})).structured_content
    assert [i["id"] for i in r["items"]] == ["modelcontextprotocol/servers", "a/b"] and r["total"] == 3 and r["next_page"] == 2
    q = route.calls.last.request.url.params
    assert (q["q"], q["per_page"], q["page"]) == ("mcp server", "2", "1")
    assert route.calls.last.request.headers["X-GitHub-Api-Version"] == "2022-11-28"
    g = respx.get(f"{BASE}/repos/modelcontextprotocol/servers").mock(return_value=httpx.Response(200, json={
        "full_name": "modelcontextprotocol/servers", "html_url": "https://github.com/modelcontextprotocol/servers", "description": "Model Context Protocol Servers"}))
    item = (await _server().call_tool("get_item", {"collection": "repositories", "item_id": "modelcontextprotocol/servers"})).structured_content
    assert item["content"] == "Model Context Protocol Servers" and g.called


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_403_and_traversal():
    respx.get(f"{BASE}/search/users").mock(return_value=httpx.Response(403, json={"message": "API rate limit exceeded for 1.2.3.4. (But here's the good news: Authenticated requests get a higher rate limit.)"}))
    r = await _server().call_tool("list_items", {"collection": "users", "query": "tony"})
    assert r.is_error and r.structured_content["error"] == "rate_limited"
    r = await _server().call_tool("get_item", {"collection": "users", "item_id": "../user/emails"})
    assert r.is_error and r.structured_content["error"] == "invalid_input"
