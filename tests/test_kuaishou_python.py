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

SPEC = json.loads((ROOT / "catalog" / "social" / "kuaishou.json").read_text(encoding="utf-8"))
CREDS = {"app_id": "ks123456", "app_secret": "KS-SECRET-9876", "refresh_token": "RT-ks-1"}
TOKEN = "https://open.kuaishou.com/oauth2/refresh_token"


def _server(creds):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], {**a["auth"], "state_key": "kuaishou"}, creds, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_uses_app_id_and_app_secret_then_query_token(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    tok = respx.get(url__startswith=TOKEN).mock(return_value=httpx.Response(200, json={"result": 1, "access_token": "AT-ks-1", "expires_in": 172800, "refresh_token": "RT-ks-2", "refresh_token_expires_in": 15552000}))
    me = respx.get(url__startswith="https://open.kuaishou.com/openapi/user_info").mock(return_value=httpx.Response(200, json={"result": 1, "user_info": {"name": "ann", "fan": 12}}))
    creds = dict(CREDS)
    res = await _server(creds).call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["user_info"]["name"] == "ann"
    assert dict(tok.calls[0].request.url.params) == {"grant_type": "refresh_token", "refresh_token": "RT-ks-1", "app_id": "ks123456", "app_secret": "KS-SECRET-9876"}
    assert dict(me.calls[0].request.url.params) == {"app_id": "ks123456", "access_token": "AT-ks-1"}
    assert "Authorization" not in me.calls[0].request.headers
    assert creds["refresh_token"] == "RT-ks-2" and json.loads((tmp_path / "kuaishou.json").read_text())["refresh_token"] == "RT-ks-2"


@pytest.mark.asyncio
@respx.mock
async def test_delete_and_analytics():
    respx.get(url__startswith=TOKEN).mock(return_value=httpx.Response(200, json={"result": 1, "access_token": "AT-ks-1", "expires_in": 172800}))
    d = respx.post(url__startswith="https://open.kuaishou.com/openapi/photo/delete").mock(return_value=httpx.Response(200, json={"result": 1}))
    respx.get(url__startswith="https://open.kuaishou.com/openapi/photo/info").mock(return_value=httpx.Response(200, json={"result": 1, "video_info": {"photo_id": "3xwn3kkerxj6g9n", "like_count": 4, "comment_count": 1, "view_count": 99}}))
    s = _server(dict(CREDS))
    r = await s.call_tool("delete", {"post_id": "3xwn3kkerxj6g9n"})
    assert r.structured_content["status"] == "deleted" and d.calls[0].request.url.params["photo_id"] == "3xwn3kkerxj6g9n"
    a = await s.call_tool("analytics_post", {"post_id": "3xwn3kkerxj6g9n"})
    assert a.structured_content["post_id"] == "3xwn3kkerxj6g9n" and a.structured_content["metrics"]["view_count"] == 99


@pytest.mark.asyncio
@respx.mock
async def test_result_code_and_discarded_refresh_token_are_errors():
    respx.get(url__startswith=TOKEN).mock(return_value=httpx.Response(200, json={"result": 100200100, "error_msg": "refreshToken.discarded"}))
    res = await _server(dict(CREDS)).call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "KS-SECRET-9876" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_non_one_result_is_an_is_error():
    respx.get(url__startswith=TOKEN).mock(return_value=httpx.Response(200, json={"result": 1, "access_token": "AT-ks-1", "expires_in": 172800}))
    respx.get(url__startswith="https://open.kuaishou.com/openapi/photo/info").mock(return_value=httpx.Response(200, json={"result": 120001, "error_msg": "视频不存在"}))
    res = await _server(dict(CREDS)).call_tool("analytics_post", {"post_id": "x"})
    assert res.is_error is True
