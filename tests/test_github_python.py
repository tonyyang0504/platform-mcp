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

SPEC = json.loads((ROOT / "catalog" / "social" / "github.json").read_text(encoding="utf-8"))


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"token": "ghp_testsecret123"}, 50, "test", envelope=a["envelope"]))


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "read_comments"]
    assert next(t for t in tools if t.name == "delete").annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_queries_discussion_comments_by_node_id():
    route = respx.post("https://api.github.com/graphql").mock(return_value=httpx.Response(200, json={"data": {"node": {"comments": {
        "totalCount": 2, "nodes": [{"id": "DC_kwDOA1", "body": "Nice", "createdAt": "2026-09-01T00:00:00Z", "url": "https://github.com/o/r/discussions/1#discussioncomment-1", "author": {"login": "octocat"}}]}}}}))
    res = await _server().call_tool("read_comments", {"post_id": "D_kwDOA", "limit": 10})
    sc = res.structured_content
    assert res.is_error is False and sc["total"] == 2 and sc["comments"][0]["author"] == "octocat" and sc["comments"][0]["text"] == "Nice"
    req = route.calls.last.request
    body = json.loads(req.content)
    assert body["variables"] == {"id": "D_kwDOA", "first": 10} and "comments(first: $first)" in body["query"]
    assert req.headers["Authorization"] == "Bearer ghp_testsecret123"


@pytest.mark.asyncio
@respx.mock
async def test_delete_runs_the_delete_discussion_mutation():
    route = respx.post("https://api.github.com/graphql").mock(return_value=httpx.Response(200, json={"data": {"deleteDiscussion": {"discussion": {"id": "D_kwDOA"}}}}))
    res = await _server().call_tool("delete", {"post_id": "D_kwDOA"})
    assert res.is_error is False and res.structured_content["status"] == "deleted"
    body = json.loads(route.calls.last.request.content)
    assert body["query"].startswith("mutation") and "deleteDiscussion" in body["query"] and body["variables"] == {"id": "D_kwDOA"}


@pytest.mark.asyncio
@respx.mock
async def test_graphql_errors_are_an_error_result_and_401_hides_the_token():
    respx.post("https://api.github.com/graphql").mock(return_value=httpx.Response(200, json={"data": None, "errors": [{"type": "FORBIDDEN", "message": "Resource not accessible by personal access token"}]}))
    res = await _server().call_tool("analytics_post", {"post_id": "D_kwDOA"})
    assert res.is_error is True
    respx.get("https://api.github.com/user").mock(return_value=httpx.Response(401, json={"message": "Bad credentials ghp_testsecret123"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "ghp_testsecret123" not in json.dumps(res.structured_content)
