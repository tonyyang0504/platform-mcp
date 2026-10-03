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

SPEC = json.loads((ROOT / "catalog" / "social" / "wykop.json").read_text(encoding="utf-8"))
BASE = "https://wykop.pl/api/v3"
CREDS = {"app_key": "devkopapp", "app_secret": "SECRETdevkop"}
COMMENT = {"id": 11, "author": {"username": "devkopuser"}, "created_at": "2019-02-25 20:35", "content": "Oto treść komentarza", "votes": {"up": 3, "down": 0}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(CREDS), 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_app_token_reads_are_offered():
    assert sorted(t.name for t in await _server().list_tools()) == ["analytics_post", "read_comments"]


@pytest.mark.asyncio
@respx.mock
async def test_app_login_uses_the_nested_body_and_comments_are_mapped():
    auth = respx.post(BASE + "/auth").mock(return_value=httpx.Response(200, json={"data": {"token": "APPJWT"}}))
    route = respx.get(BASE + "/entries/2341/comments").mock(return_value=httpx.Response(200, json={"data": [COMMENT, {**COMMENT, "id": 12}], "pagination": {"per_page": 2, "total": 45}}))
    res = await _server().call_tool("read_comments", {"post_id": "2341", "page": 2, "limit": 2})
    assert res.is_error is False, res.structured_content
    c = res.structured_content["comments"]
    assert [x["id"] for x in c] == ["11", "12"] and c[0]["author"] == "devkopuser" and c[0]["text"] == "Oto treść komentarza"
    assert res.structured_content["total"] == 45 and res.structured_content["next_page"] == 3
    assert json.loads(auth.calls.last.request.content) == {"data": {"key": "devkopapp", "secret": "SECRETdevkop"}}
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer APPJWT" and dict(req.url.params) == {"page": "2", "limit": "2"}


@pytest.mark.asyncio
@respx.mock
async def test_analytics_post_reads_entry_votes_and_relogs_on_401():
    auth = respx.post(BASE + "/auth").mock(side_effect=[httpx.Response(200, json={"data": {"token": "OLD"}}), httpx.Response(200, json={"data": {"token": "NEW"}})])
    respx.get(BASE + "/entries/2341").mock(side_effect=[httpx.Response(401, json={"code": 401}),
                                                        httpx.Response(200, json={"data": {"id": 2341, "votes": {"up": 23, "down": 5}, "comments": {"count": 5}}})])
    res = await _server().call_tool("analytics_post", {"post_id": "2341"})
    assert res.is_error is False, res.structured_content
    assert res.structured_content["post_id"] == "2341" and res.structured_content["metrics"] == {"up": 23, "down": 5}
    assert auth.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_wrong_app_secret_is_an_auth_error():
    respx.post(BASE + "/auth").mock(return_value=httpx.Response(401, json={"code": 401, "error": {"message": "Username could not be found."}}))
    res = await _server().call_tool("read_comments", {"post_id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
