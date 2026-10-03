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

SPEC = json.loads((ROOT / "catalog" / "social" / "mastodon.json").read_text(encoding="utf-8"))


def _server():
    # `instance` is a non-secret config field: every tool path is https://{instance}/api/v1/...
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "T", "instance": "mastodon.example"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "publish_text", "read_comments", "read_mentions", "reply_comment"]
    assert next(t for t in tools if t.name == "delete").annotations.destructive_hint is True
    pt = next(t for t in tools if t.name == "publish_text")
    assert pt.annotations.read_only_hint is False and pt.annotations.destructive_hint is False and pt.input_schema["required"] == ["text"]
    rm = next(t for t in tools if t.name == "read_mentions")
    assert rm.annotations.read_only_hint is True and rm.output_schema["properties"]["mentions"]["type"] == "array"


@pytest.mark.asyncio
@respx.mock
async def test_delete_removes_the_status_and_answers_a_literal_status():
    # docs.joinmastodon.org/methods/statuses/#delete -> 200 with the deleted Status (source `text` for reposting)
    route = respx.delete("https://mastodon.example/api/v1/statuses/103254962155278888").mock(return_value=httpx.Response(200, json={
        "id": "103254962155278888", "text": "test content", "created_at": "2019-12-05T11:34:47.196Z", "account": {"id": "1", "acct": "me"}}))
    res = await _server().call_tool("delete", {"post_id": "103254962155278888"})
    assert res.is_error is False and res.structured_content["status"] == "deleted" and res.structured_content["raw"]["text"] == "test content"
    assert route.calls.last.request.headers["Authorization"] == "Bearer T"
    respx.delete("https://mastodon.example/api/v1/statuses/1").mock(return_value=httpx.Response(404, json={"error": "Record not found"}))
    res = await _server().call_tool("delete", {"post_id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_posts_a_status_to_the_configured_instance():
    # docs.joinmastodon.org/methods/statuses/#create -> Status {id, uri, url, created_at, content, account}
    route = respx.post("https://mastodon.example/api/v1/statuses").mock(return_value=httpx.Response(200, json={
        "id": "103254962155278888", "uri": "https://mastodon.example/users/me/statuses/103254962155278888", "url": "https://mastodon.example/@me/103254962155278888",
        "created_at": "2019-12-05T11:34:47.196Z", "content": "<p>test content</p>", "visibility": "public", "account": {"id": "1", "username": "me", "acct": "me"}}))
    res = await _server().call_tool("publish_text", {"text": "test content"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "103254962155278888" and sc["url"].endswith("/@me/103254962155278888") and sc["created_at"].startswith("2019-12-05")
    req = route.calls.last.request
    assert json.loads(req.content) == {"status": "test content"} and req.headers["Authorization"] == "Bearer T"


@pytest.mark.asyncio
@respx.mock
async def test_read_mentions_filters_notifications_by_type_and_maps_the_status():
    # docs.joinmastodon.org/methods/notifications/#get
    respx.get("https://mastodon.example/api/v1/notifications").mock(return_value=httpx.Response(200, json=[
        {"id": "34975861", "type": "mention", "created_at": "2019-11-23T07:49:02.064Z", "account": {"id": "971724", "username": "zsc", "acct": "zsc"},
         "status": {"id": "103186126728896492", "created_at": "2019-11-23T07:49:01.940Z", "content": "<p>@trwnh sup!</p>"}}]))
    res = await _server().call_tool("read_mentions", {"since": "34975000"})
    assert res.is_error is False
    m = res.structured_content["mentions"][0]
    assert m["id"] == "34975861" and m["author"] == "zsc" and m["text"] == "<p>@trwnh sup!</p>" and res.structured_content["next_page"] is None
    params = respx.calls.last.request.url.params
    assert params["types[]"] == "mention" and params["limit"] == "40" and params["since_id"] == "34975000" and "page" not in params


@pytest.mark.asyncio
@respx.mock
async def test_revoked_token_is_an_auth_error_result():
    respx.get("https://mastodon.example/api/v1/accounts/verify_credentials").mock(return_value=httpx.Response(401, json={"error": "The access token is invalid"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
