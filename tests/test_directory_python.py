"""Directory server (`platform-mcp-hub directory`): tools over the catalog snapshot (catalog/directory.json)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime" / "python"))
from platform_mcp_hub.directory import build_server, data  # noqa: E402


def _payload(res):
    return res.structured_content or json.loads(res.content[0].text)


@pytest.fixture(scope="module")
def server():
    return build_server()


async def test_tools_are_read_only(server):
    tools = await server.list_tools()
    assert sorted(t.name for t in tools) == ["describe_platform", "list_categories", "list_platforms", "search_capabilities"]
    for t in tools:
        assert t.annotations.read_only_hint is True and t.annotations.destructive_hint is False


async def test_categories_and_counts(server):
    out = _payload(await server.call_tool("list_categories", {}))
    cats = {c["category"]: c for c in out["categories"]}
    assert cats["jobs"]["platforms"] > 200 and cats["jobs"]["served"] >= 9
    assert "search" in cats["jobs"]["verbs"] and "get_ticker" in cats["trading"]["verbs"]
    assert sum(c["platforms"] for c in out["categories"]) == len(data()["platforms"])


async def test_list_platforms_filters_and_pages(server):
    out = _payload(await server.call_tool("list_platforms", {"category": "jobs", "served_only": True, "limit": 3}))
    assert out["total"] >= 9 and len(out["items"]) == 3 and all(i["served"] and i["category"] == "jobs" for i in out["items"])
    page2 = _payload(await server.call_tool("list_platforms", {"category": "jobs", "served_only": True, "limit": 3, "offset": 3}))
    assert {i["id"] for i in page2["items"]}.isdisjoint({i["id"] for i in out["items"]})
    q = _payload(await server.call_tool("list_platforms", {"query": "reed"}))
    assert any(i["id"] == "reed" for i in q["items"])


async def test_describe_served_platform_has_install(server):
    out = _payload(await server.call_tool("describe_platform", {"platform_id": "reed"}))
    assert out["served"] and out["tools"] == ["get_posting", "me", "search"]
    # platform-mcp-hub is not published yet (catalog/schema/release.json): run from source, never `uvx <name>`
    inst = out["install"]
    assert inst["status"] == "unpublished" and not {"pip", "uvx", "npx", "claude_desktop"} & set(inst)
    assert inst["serve"] == "platform-mcp-hub serve reed"
    assert inst["from_source"]["python"] == "uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve reed"
    assert inst["from_source"]["typescript"].endswith("node dist/cli.js serve reed")
    assert out["serve"] == "reed" and out["registry_name"] == "io.github.tonyyang0504/reed-mcp"
    assert out["credentials"][0]["env"] == "PLATFORM_MCP_REED_API_KEY" and inst["env"] == {"PLATFORM_MCP_REED_API_KEY": "<value>"}
    assert out["verbs"]["search"]["read_only"] is True


async def test_describe_unserved_and_missing(server):
    unserved = next(p for p in data()["platforms"] if not p["served"])
    out = _payload(await server.call_tool("describe_platform", {"platform_id": unserved["id"]}))
    assert "how_to_add" in out and "install" not in out
    res = await server.call_tool("describe_platform", {"platform_id": "no-such-platform"})
    assert _payload(res)["error"] == "not_found"


async def test_search_capabilities_prefers_served(server):
    out = _payload(await server.call_tool("search_capabilities", {"capability": "search", "category": "jobs"}))
    assert out["total"] >= 9 and out["items"][0]["served"] is True and out["items"][0]["matched"] == "tool"
    caps = _payload(await server.call_tool("search_capabilities", {"capability": "job_search", "served_only": False, "limit": 5}))
    assert caps["total"] >= 1 and all(i["matched"] in ("tool", "capability") for i in caps["items"])


async def test_an_id_served_in_two_categories_is_served_by_category(server):
    out = _payload(await server.call_tool("list_platforms", {"query": "linkedin", "served_only": True}))
    refs = {i["category"]: _payload(await server.call_tool("describe_platform", {"platform_id": i["id"]}))["serve"] for i in out["items"] if i["id"] == "linkedin"}
    assert set(refs.values()) <= {"ads/linkedin", "social/linkedin"} and refs


def test_published_hints_name_the_hub(monkeypatch):
    from platform_mcp_hub import directory
    monkeypatch.setattr(directory, "_DATA", {**data(), "snapshot": {**data()["snapshot"], "published": True}})
    reed = next(p for p in directory.data()["platforms"] if p["id"] == "reed")
    hints = directory.install_hints(reed)
    assert hints["uvx"] == "uvx platform-mcp-hub serve reed" and hints["npx"] == "npx -y platform-mcp-hub serve reed"
    assert hints["claude_desktop"]["mcpServers"]["reed"]["args"] == ["platform-mcp-hub", "serve", "reed"] and "status" not in hints
