"""Runtime features shared by every server: path-token auth, ok:false envelopes, zero-based
pages, per-install config fields, empty-record 404."""
import json
import re
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = {
    "id": "fake", "category": "messaging", "label": "Fake", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
    "adapter": {
        "base_url": "https://api.example/bot{token}", "auth": {"type": "path", "field": "token", "fields": [{"name": "token", "help": "bot token"}]},
        "config_fields": [{"name": "sender", "required": False, "help": "default sender"}],
        "envelope": {"ok_field": "ok", "error_field": "description"},
        "rate_per_second": 50,
        "tools": {
            "me": {"kind": "probe", "path": "/getMe"},
            "send": {"method": "POST", "path": "/sendMessage", "body": {"chat_id": "to", "text": "text", "from": "@sender"}, "result": {"root": "result", "fields": {"message_id": "message_id", "status": "=sent"}}},
            "list_inbound": {"path": "/getUpdates", "params": {"offset": "page0", "limit": "limit"}, "result": {"items": "result", "key": "messages", "fields": {"id": "update_id", "text": "message.text"}}},
        },
    },
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "T0K", "sender": "bot@example"}, 50, "test", envelope=SPEC["adapter"]["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_path_token_config_field_and_zero_based_page():
    route = respx.post("https://api.example/botT0K/sendMessage").mock(return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 7}}))
    res = await _server().call_tool("send", {"to": "123", "text": "hi"})
    assert res.is_error is False and res.structured_content["message_id"] == "7"
    body = route.calls.last.request.content
    assert b'"from": "bot@example"' in body or b'"from":"bot@example"' in body
    respx.get("https://api.example/botT0K/getUpdates").mock(return_value=httpx.Response(200, json={"ok": True, "result": [{"update_id": 1, "message": {"text": "x"}}]}))
    res = await _server().call_tool("list_inbound", {"page": 1})
    assert res.structured_content["messages"][0]["id"] == "1"
    assert respx.calls.last.request.url.params["offset"] == "0"


@pytest.mark.asyncio
@respx.mock
async def test_ok_false_envelope_is_an_is_error_result():
    respx.get("https://api.example/botT0K/getMe").mock(return_value=httpx.Response(200, json={"ok": False, "description": "Unauthorized"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"


@pytest.mark.asyncio
@respx.mock
async def test_empty_record_is_not_found():
    respx.post("https://api.example/botT0K/sendMessage").mock(return_value=httpx.Response(200, json={"ok": True, "result": {}}))
    res = await _server().call_tool("send", {"to": "1", "text": "x"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and res.structured_content["http_status"] == 404


SESSION_SPEC = {
    "id": "sess", "category": "social", "label": "Sess", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
    "adapter": {
        "base_url": "https://api.example", "rate_per_second": 50,
        "auth": {"type": "session", "login": {"method": "POST", "path": "/login", "body": {"identifier": "@identifier", "password": "@password"}}, "token_path": "accessJwt", "token_ttl_seconds": 600,
                 "fields": [{"name": "identifier"}, {"name": "password"}]},
        "tools": {"me": {"kind": "probe", "path": "/me"}},
    },
}
OAUTH_SPEC = {
    "id": "oa", "category": "social", "label": "OA", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
    "adapter": {
        "base_url": "https://api.example", "rate_per_second": 50,
        "auth": {"type": "oauth2_client_credentials", "token_url": "https://auth.example/token", "fields": [{"name": "client_id"}, {"name": "client_secret"}]},
        "tools": {"me": {"kind": "probe", "path": "/me"}},
    },
}


@pytest.mark.asyncio
@respx.mock
async def test_session_login_then_bearer_and_relogin_on_401():
    login = respx.post("https://api.example/login").mock(side_effect=[httpx.Response(200, json={"accessJwt": "T1"}), httpx.Response(200, json={"accessJwt": "T2"})])
    me = respx.get("https://api.example/me").mock(side_effect=[httpx.Response(401), httpx.Response(200, json={"handle": "x"})])
    t = Transport(SESSION_SPEC["adapter"]["base_url"], SESSION_SPEC["adapter"]["auth"], {"identifier": "u", "password": "p"}, 50, "test")
    res = await build_server(SESSION_SPEC, transport=t).call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["handle"] == "x"
    assert login.call_count == 2 and me.call_count == 2
    assert me.calls.last.request.headers["Authorization"] == "Bearer T2"
    assert b'"identifier": "u"' in login.calls[0].request.content or b'"identifier":"u"' in login.calls[0].request.content


@pytest.mark.asyncio
@respx.mock
async def test_oauth2_client_credentials_uses_basic_form_post():
    tok = respx.post("https://auth.example/token").mock(return_value=httpx.Response(200, json={"access_token": "AT", "expires_in": 3600}))
    respx.get("https://api.example/me").mock(return_value=httpx.Response(200, json={"name": "n"}))
    t = Transport(OAUTH_SPEC["adapter"]["base_url"], OAUTH_SPEC["adapter"]["auth"], {"client_id": "id", "client_secret": "sec"}, 50, "test")
    res = await build_server(OAUTH_SPEC, transport=t).call_tool("me", {})
    assert res.is_error is False
    assert tok.calls.last.request.headers["Authorization"].startswith("Basic ") and b"grant_type=client_credentials" in tok.calls.last.request.content
    assert respx.calls.last.request.headers["Authorization"] == "Bearer AT"


TYPED_SPEC = {
    "id": "typed", "category": "ecommerce_channels", "label": "Typed", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
    "adapter": {
        "base_url": "https://api.example", "rate_per_second": 50, "auth": {"type": "bearer", "field": "token", "fields": [{"name": "token"}]},
        "tools": {
            "set_inventory": {"method": "PUT", "path": "/products/{listing_id}", "body": {"manage_stock": "json:true", "stock_quantity": "quantity", "regular_price": "str:quantity", "weight": "json:0"}, "result": {"fields": {"listing_id": "id"}}},
            "end_listing": {"method": "DELETE", "path": "/products/{listing_id}", "result": {"fields": {"listing_id": "=gone", "status": "=ended"}}},
        },
    },
}


@pytest.mark.asyncio
@respx.mock
async def test_typed_literals_and_string_coercion_in_bodies():
    route = respx.put("https://api.example/products/9").mock(return_value=httpx.Response(200, json={"id": 9}))
    server = build_server(TYPED_SPEC, transport=Transport("https://api.example", TYPED_SPEC["adapter"]["auth"], {"token": "t"}, 50, "test"))
    res = await server.call_tool("set_inventory", {"listing_id": "9", "quantity": 3})
    assert res.is_error is False
    import json as _json
    body = _json.loads(route.calls[0].request.content)
    assert body == {"manage_stock": True, "stock_quantity": 3, "regular_price": "3", "weight": 0}


@pytest.mark.asyncio
@respx.mock
async def test_empty_204_body_is_a_result_not_a_crash():
    respx.delete("https://api.example/products/9").mock(return_value=httpx.Response(204))
    server = build_server(TYPED_SPEC, transport=Transport("https://api.example", TYPED_SPEC["adapter"]["auth"], {"token": "t"}, 50, "test"))
    res = await server.call_tool("end_listing", {"listing_id": "9"})
    assert res.is_error is False and res.structured_content["status"] == "ended"


@pytest.mark.asyncio
@respx.mock
async def test_require_drops_feed_rows_without_the_listed_fields():
    spec = {"id": "feed", "category": "jobs", "label": "Feed", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://feed.example", "rate_per_second": 50, "auth": {"type": "none", "fields": []},
                        "tools": {"search": {"path": "/api", "result": {"items": "$", "key": "postings", "require": ["id"], "fields": {"id": "id", "title": "position"}}}}}}
    respx.get("https://feed.example/api").mock(return_value=httpx.Response(200, json=[{"legal": "terms"}, {"id": 1, "position": "Dev"}, {"id": None, "position": "x"}]))
    server = build_server(spec, transport=Transport("https://feed.example", spec["adapter"]["auth"], {}, 50, "test"))
    res = await server.call_tool("search", {"query": "dev"})
    assert res.is_error is False and [p["id"] for p in res.structured_content["postings"]] == ["1"]


@pytest.mark.asyncio
@respx.mock
async def test_fixed_headers_and_uuid_expression():
    spec = {"id": "mx", "category": "messaging", "label": "Mx", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://mx.example", "rate_per_second": 50, "auth": {"type": "bearer", "field": "token", "fields": [{"name": "token"}]},
                        "headers": {"X-Crisp-Tier": "plugin"},
                        "tools": {"send": {"method": "PUT", "path": "/rooms/{to}/send/m.room.message/{txn}", "path_params": {"txn": "uuid"}, "body": {"msgtype": "=m.text", "body": "text"}, "result": {"fields": {"message_id": "event_id", "status": "=sent"}}}}}}
    route = respx.put(url__regex=r"https://mx\.example/rooms/r1/send/m\.room\.message/[0-9a-f-]{36}$").mock(return_value=httpx.Response(200, json={"event_id": "$e1"}))
    server = build_server(spec)  # real Transport: exercises fixed headers
    import os
    os.environ["PLATFORM_MCP_MX_TOKEN"] = "t"
    try:
        r1 = await server.call_tool("send", {"to": "r1", "text": "hi"})
        r2 = await server.call_tool("send", {"to": "r1", "text": "hi"})
    finally:
        del os.environ["PLATFORM_MCP_MX_TOKEN"]
    assert r1.is_error is False and r1.structured_content["message_id"] == "$e1"
    assert route.calls[0].request.headers["X-Crisp-Tier"] == "plugin" and route.calls[0].request.headers["Authorization"] == "Bearer t"
    assert route.calls[0].request.url.path != route.calls[1].request.url.path  # a fresh uuid per call


@pytest.mark.asyncio
@respx.mock
async def test_digit_segments_in_body_keys_build_arrays():
    spec = {"id": "sg", "category": "messaging", "label": "Sg", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://sg.example", "rate_per_second": 50, "auth": {"type": "bearer", "field": "api_key", "fields": [{"name": "api_key"}]},
                        "tools": {"send": {"method": "POST", "path": "/v3/mail/send", "body": {"personalizations.0.to.0.email": "to", "from.email": "@sender", "subject": "subject", "content.0.type": "=text/plain", "content.0.value": "text"}, "result": {"fields": {"status": "=queued"}}}}}}
    route = respx.post("https://sg.example/v3/mail/send").mock(return_value=httpx.Response(202))
    server = build_server(spec, transport=Transport("https://sg.example", spec["adapter"]["auth"], {"api_key": "k", "sender": "me@x"}, 50, "test"))
    res = await server.call_tool("send", {"to": "a@b", "subject": "s", "text": "hi"})
    assert res.is_error is False and res.structured_content["status"] == "queued"
    import json as _json
    assert _json.loads(route.calls[0].request.content) == {"personalizations": [{"to": [{"email": "a@b"}]}], "from": {"email": "me@x"}, "subject": "s", "content": [{"type": "text/plain", "value": "hi"}]}


@pytest.mark.asyncio
@respx.mock
async def test_escaped_dots_in_body_keys():
    spec = {"id": "mx2", "category": "messaging", "label": "Mx2", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://mx.example", "rate_per_second": 50, "auth": {"type": "none", "fields": []},
                        "tools": {"reply": {"method": "PUT", "path": "/rooms/{channel}/send/m.room.message/{txn}", "path_params": {"txn": "uuid"}, "body": {"msgtype": "=m.text", "body": "text", "m\\.relates_to.rel_type": "=m.thread", "m\\.relates_to.event_id": "thread_id", "m\\.relates_to.m\\.in_reply_to.event_id": "thread_id"}, "result": {"fields": {"message_id": "event_id", "status": "=sent"}}}}}}
    route = respx.put(url__regex=r"https://mx\.example/rooms/r1/send/.*").mock(return_value=httpx.Response(200, json={"event_id": "$e2"}))
    server = build_server(spec, transport=Transport("https://mx.example", spec["adapter"]["auth"], {}, 50, "test"))
    res = await server.call_tool("reply", {"channel": "r1", "thread_id": "$t", "text": "yo"})
    assert res.is_error is False
    import json as _json
    assert _json.loads(route.calls[0].request.content) == {"msgtype": "m.text", "body": "yo", "m.relates_to": {"rel_type": "m.thread", "event_id": "$t", "m.in_reply_to": {"event_id": "$t"}}}


@pytest.mark.asyncio
@respx.mock
async def test_array_element_and_int_coercion_and_instance_login():
    spec = {"id": "lem", "category": "social", "label": "Lem", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://{instance}", "rate_per_second": 50,
                        "auth": {"type": "session", "login": {"method": "POST", "path": "/api/v3/user/login", "body": {"username_or_email": "@user", "password": "@password"}}, "token_path": "jwt", "token_ttl_seconds": 600, "fields": [{"name": "user"}, {"name": "password"}]},
                        "config_fields": [{"name": "instance", "required": True}, {"name": "community_id", "required": True}],
                        "tools": {"publish_image": {"method": "POST", "path": "/api/v3/post", "body": {"community_id": "int:@community_id", "name": "text", "url": "image_urls.0"}, "result": {"root": "post_view.post", "fields": {"id": "id"}}}}}}
    login = respx.post("https://lemmy.example/api/v3/user/login").mock(return_value=httpx.Response(200, json={"jwt": "J"}))
    post = respx.post("https://lemmy.example/api/v3/post").mock(return_value=httpx.Response(200, json={"post_view": {"post": {"id": 42}}}))
    server = build_server(spec, transport=Transport("https://{instance}", spec["adapter"]["auth"], {"user": "u", "password": "p", "instance": "lemmy.example", "community_id": "7"}, 50, "test"))
    res = await server.call_tool("publish_image", {"text": "hi", "image_urls": ["https://i/1.png", "https://i/2.png"]})
    assert res.is_error is False and res.structured_content["id"] == "42"
    import json as _json
    assert login.called and post.calls[0].request.headers["Authorization"] == "Bearer J"
    assert _json.loads(post.calls[0].request.content) == {"community_id": 7, "name": "hi", "url": "https://i/1.png"}
    bad = build_server(spec, transport=Transport("https://{instance}", spec["adapter"]["auth"], {"user": "u", "password": "p", "instance": "lemmy.example", "community_id": "seven"}, 50, "test"))
    res = await bad.call_tool("publish_image", {"text": "hi", "image_urls": ["x"]})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_oauth2_refresh_token_grant_with_body_client_auth_and_extra_headers():
    spec = {"id": "ets", "category": "ecommerce_channels", "label": "Ets", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://api.ets.example/v3", "rate_per_second": 50,
                        "auth": {"type": "oauth2_refresh_token", "token_url": "https://api.ets.example/v3/public/oauth/token", "client_auth": "body",
                                 "extra_headers": {"x-api-key": "client_id"}, "fields": [{"name": "client_id"}, {"name": "refresh_token"}]},
                        "tools": {"me": {"kind": "probe", "path": "/application/users/me"}}}}
    token = respx.post("https://api.ets.example/v3/public/oauth/token").mock(side_effect=[httpx.Response(200, json={"access_token": "A1", "expires_in": 3600}), httpx.Response(200, json={"access_token": "A2", "expires_in": 3600})])
    me = respx.get("https://api.ets.example/v3/application/users/me").mock(side_effect=[httpx.Response(200, json={"user_id": 1}), httpx.Response(401, json={"error": "expired"}), httpx.Response(200, json={"user_id": 1})])
    server = build_server(spec, transport=Transport(spec["adapter"]["base_url"], spec["adapter"]["auth"], {"client_id": "cid", "refresh_token": "R"}, 50, "test"))
    first = await server.call_tool("me", {})
    assert first.is_error is False
    form = dict(x.split("=") for x in token.calls[0].request.content.decode().split("&"))
    assert form == {"grant_type": "refresh_token", "refresh_token": "R", "client_id": "cid"} and "Authorization" not in token.calls[0].request.headers
    assert me.calls[0].request.headers["Authorization"] == "Bearer A1" and me.calls[0].request.headers["x-api-key"] == "cid"
    second = await server.call_tool("me", {})  # 401 → re-mint from the refresh token → retry once
    assert second.is_error is False and me.calls[2].request.headers["Authorization"] == "Bearer A2" and token.call_count == 2


ROT_SPEC = {"id": "rot", "category": "ecommerce_channels", "label": "Rot", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://api.rot.example", "rate_per_second": 50, "headers": {"Content-Type": "application/vnd.rot.v1+json"},
                        "auth": {"type": "oauth2_refresh_token", "token_url": "https://api.rot.example/token", "client_auth": "body", "fields": [{"name": "client_id"}, {"name": "client_secret"}, {"name": "refresh_token"}]},
                        "tools": {"me": {"kind": "probe", "path": "/me"},
                                  "update_listing": {"method": "PUT", "path": "/offers/{listing_id}", "body": {"price": "str:price"}, "result": {"fields": {"listing_id": "id"}}},
                                  "create_listing": {"method": "POST", "path": "/listings", "body_format": "form", "body": {"title": "title", "quantity": "int:quantity", "is_supply": "json:false"}, "result": {"fields": {"listing_id": "listing_id"}}}}}}


@pytest.mark.asyncio
@respx.mock
async def test_rotating_refresh_token_is_reused_and_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    token = respx.post("https://api.rot.example/token").mock(side_effect=[
        httpx.Response(200, json={"access_token": "ACCESS-ONE", "refresh_token": "REFRESH-TWO", "expires_in": 3600}),
        httpx.Response(200, json={"access_token": "ACCESS-TWO", "refresh_token": "REFRESH-THREE", "expires_in": 3600})])
    respx.get("https://api.rot.example/me").mock(side_effect=[httpx.Response(200, json={"id": 1}), httpx.Response(401), httpx.Response(200, json={"id": 1})])
    auth = {**ROT_SPEC["adapter"]["auth"], "state_key": "rot"}
    server = build_server(ROT_SPEC, transport=Transport("https://api.rot.example", auth, {"client_id": "cid", "client_secret": "SECRET-XYZ", "refresh_token": "REFRESH-ONE"}, 50, "test"))
    assert (await server.call_tool("me", {})).is_error is False
    assert (await server.call_tool("me", {})).is_error is False
    forms = [dict(x.split("=") for x in c.request.content.decode().split("&")) for c in token.calls]
    assert forms[0]["refresh_token"] == "REFRESH-ONE" and forms[1]["refresh_token"] == "REFRESH-TWO"
    import json as _json, os, stat
    saved = tmp_path / "rot.json"
    assert _json.loads(saved.read_text())["refresh_token"] == "REFRESH-THREE"
    assert stat.S_IMODE(os.stat(saved).st_mode) == 0o600
    fresh = Transport("https://api.rot.example", auth, {"client_id": "cid", "client_secret": "s", "refresh_token": "STALE-FROM-ENV"}, 50, "test")
    assert fresh.creds["refresh_token"] == "REFRESH-THREE"  # a restart picks up the rotated token


@pytest.mark.asyncio
@respx.mock
async def test_error_bodies_never_echo_known_secrets():
    respx.post("https://api.rot.example/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "refresh_token": "REFRESH-ONE", "hint": "client SECRET-XYZ rejected"}))
    server = build_server(ROT_SPEC, transport=Transport("https://api.rot.example", ROT_SPEC["adapter"]["auth"], {"client_id": "cid", "client_secret": "SECRET-XYZ", "refresh_token": "REFRESH-ONE"}, 50, "test"))
    res = await server.call_tool("me", {})
    text = res.content[0].text
    assert res.is_error is True and "REFRESH-ONE" not in text and "SECRET-XYZ" not in text and "<redacted>" in text


@pytest.mark.asyncio
@respx.mock
async def test_form_bodies_and_vendor_content_type_are_kept():
    respx.post("https://api.rot.example/token").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-ONE", "expires_in": 3600}))
    form = respx.post("https://api.rot.example/listings").mock(return_value=httpx.Response(200, json={"listing_id": 5}))
    put = respx.put("https://api.rot.example/offers/9").mock(return_value=httpx.Response(200, json={"id": 9}))
    transport = Transport("https://api.rot.example", ROT_SPEC["adapter"]["auth"], {"client_id": "cid", "client_secret": "SECRET-XYZ", "refresh_token": "REFRESH-ONE"}, 50, "test")
    transport.fixed_headers = ROT_SPEC["adapter"]["headers"]
    server = build_server(ROT_SPEC, transport=transport)
    assert (await server.call_tool("create_listing", {"title": "Mug", "price": 9.5, "quantity": 3})).is_error is False
    req = form.calls[0].request
    assert req.headers["Content-Type"].startswith("application/x-www-form-urlencoded") or req.headers["Content-Type"] == "application/vnd.rot.v1+json"
    assert dict(x.split("=") for x in req.content.decode().split("&")) == {"title": "Mug", "quantity": "3", "is_supply": "false"}
    assert (await server.call_tool("update_listing", {"listing_id": "9", "price": 12})).is_error is False
    assert put.calls[0].request.headers["Content-Type"] == "application/vnd.rot.v1+json"


ADS_SPEC = {"id": "adz", "category": "ads", "label": "Adz", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://api.adz.example", "rate_per_second": 50, "auth": {"type": "bearer", "field": "token", "fields": [{"name": "token"}]},
                        "tools": {
                            "pause_resume": {"method": "POST", "path": "/campaigns/{campaign_id}", "headers": {"X-RestLi-Method": "PARTIAL_UPDATE"},
                                             "body": {"status": "map:action:pause=PAUSED,resume=ACTIVE"}, "result": {"fields": {"campaign_id": "=ok", "status": "=updated"}}},
                            "list_campaigns": {"path": "/adCampaigns?q=search", "query_safe": "(),:", "params": {"search": "=(status:(values:List(ACTIVE)))", "count": "limit"},
                                               "result": {"items": "elements", "key": "campaigns", "fields": {"id": "id", "name": "name"}}},
                            "update_budget": {"method": "PATCH", "path": "/ad_accounts/{ad_account}/campaigns", "path_params": {"ad_account": "@ad_account"}, "body": {"0.id": "campaign_id", "0.daily_spend_cap": "int:daily_budget"},
                                              "result": {"fields": {"campaign_id": "=ok", "status": "=updated"}}}}}}


def _ads_server():
    return build_server(ADS_SPEC, transport=Transport("https://api.adz.example", ADS_SPEC["adapter"]["auth"], {"token": "TOKEN-123", "ad_account": "9"}, 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_enum_map_and_per_tool_headers():
    route = respx.post("https://api.adz.example/campaigns/7").mock(return_value=httpx.Response(204))
    res = await _ads_server().call_tool("pause_resume", {"campaign_id": "7", "action": "pause"})
    assert res.is_error is False
    import json as _json
    assert _json.loads(route.calls[0].request.content) == {"status": "PAUSED"}
    assert route.calls[0].request.headers["X-RestLi-Method"] == "PARTIAL_UPDATE"


@pytest.mark.asyncio
@respx.mock
async def test_inline_query_and_literal_restli_characters():
    route = respx.get(url__startswith="https://api.adz.example/adCampaigns").mock(return_value=httpx.Response(200, json={"elements": [{"id": 1, "name": "A"}]}))
    res = await _ads_server().call_tool("list_campaigns", {"account_id": "9", "limit": 10})
    assert res.is_error is False
    assert str(route.calls[0].request.url) == "https://api.adz.example/adCampaigns?q=search&search=(status:(values:List(ACTIVE)))&count=10"


@pytest.mark.asyncio
@respx.mock
async def test_top_level_array_body_and_strict_integers():
    route = respx.patch("https://api.adz.example/ad_accounts/9/campaigns").mock(return_value=httpx.Response(200, json={}))
    ok = await _ads_server().call_tool("update_budget", {"account_id": "9", "campaign_id": "5", "daily_budget": 1200})
    assert ok.is_error is False
    import json as _json
    assert _json.loads(route.calls[0].request.content) == [{"id": "5", "daily_spend_cap": 1200}]
    bad = await _ads_server().call_tool("update_budget", {"account_id": "9", "campaign_id": "5", "daily_budget": 12.5})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_fmt_templates_and_date_parts():
    spec = {"id": "gads", "category": "ads", "label": "G", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://g.example", "rate_per_second": 50, "auth": {"type": "bearer", "field": "token", "fields": [{"name": "token"}]},
                        "tools": {"pause_resume": {"method": "POST", "path": "/customers/{cid}/campaigns:mutate", "path_params": {"cid": "@customer_id"},
                                                   "body": {"operations.0.update.resourceName": "fmt:customers/{@customer_id}/campaigns/{campaign_id}", "operations.0.update.status": "map:action:pause=PAUSED,resume=ENABLED", "operations.0.updateMask": "=status"},
                                                   "result": {"fields": {"campaign_id": "results.0.resourceName", "status": "=updated"}}},
                                  "get_report": {"path": "/analytics?q=analytics", "query_safe": "(),:", "params": {"dateRange": "fmt:(start:(year:{year:date_from},month:{month:date_from},day:{day:date_from}))"}, "result": {"raw": True}}}}}
    mutate = respx.post("https://g.example/customers/111/campaigns:mutate").mock(return_value=httpx.Response(200, json={"results": [{"resourceName": "customers/111/campaigns/7"}]}))
    report = respx.get(url__startswith="https://g.example/analytics").mock(return_value=httpx.Response(200, json={"elements": []}))
    server = build_server(spec, transport=Transport("https://g.example", spec["adapter"]["auth"], {"token": "TOKEN-9", "customer_id": "111"}, 50, "test"))
    res = await server.call_tool("pause_resume", {"campaign_id": "7", "action": "pause"})
    assert res.is_error is False
    import json as _json
    assert _json.loads(mutate.calls[0].request.content) == {"operations": [{"update": {"resourceName": "customers/111/campaigns/7", "status": "PAUSED"}, "updateMask": "status"}]}
    await server.call_tool("get_report", {"account_id": "1", "date_from": "2026-09-01", "date_to": "2026-09-24"})
    assert str(report.calls[0].request.url).endswith("dateRange=(start:(year:2026,month:9,day:1))")


@pytest.mark.asyncio
@respx.mock
async def test_date_expression_blocks_query_injection():
    spec = {"id": "gq", "category": "ads", "label": "G", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://g.example", "rate_per_second": 50, "auth": {"type": "none", "fields": []},
                        "tools": {"get_report": {"method": "POST", "path": "/search", "body": {"query": "fmt:SELECT x FROM t WHERE d BETWEEN '{date:date_from}' AND '{date:date_to}'"}}}}}
    route = respx.post("https://g.example/search").mock(return_value=httpx.Response(200, json={}))
    server = build_server(spec, transport=Transport("https://g.example", spec["adapter"]["auth"], {}, 50, "test"))
    ok = await server.call_tool("get_report", {"account_id": "1", "date_from": "2026-09-01", "date_to": "2026-09-24"})
    assert ok.is_error is False
    import json as _json
    assert _json.loads(route.calls[0].request.content)["query"] == "SELECT x FROM t WHERE d BETWEEN '2026-09-01' AND '2026-09-24'"
    bad = await server.call_tool("get_report", {"account_id": "1", "date_from": "2026-09-01' OR '1'='1", "date_to": "2026-09-24"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input" and route.call_count == 1


SIGN_BINANCE = {"id": "bnx", "category": "trading", "label": "Bnx", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
                "adapter": {"base_url": "https://api.bnx.example", "rate_per_second": 50,
                            "auth": {"type": "header", "header": "X-MBX-APIKEY", "field": "api_key", "fields": [{"name": "api_key"}, {"name": "api_secret"}],
                                     "sign": {"payload": "{query}", "key_field": "api_secret", "timestamp_param": "timestamp", "signature_param": "signature"}},
                            "tools": {"get_balances": {"path": "/api/v3/account", "fixed_params": {"omitZeroBalances": "true"}, "result": {"items": "balances", "key": "balances", "fields": {"asset": "asset", "free": "free"}}}}}}
SIGN_BYBIT = {"id": "byb", "category": "trading", "label": "Byb", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
              "adapter": {"base_url": "https://api.byb.example", "rate_per_second": 50, "envelope": {"ok_field": "retCode", "ok_value": 0, "error_field": "retMsg"},
                          "auth": {"type": "none", "fields": [{"name": "api_key"}, {"name": "api_secret"}],
                                   "sign": {"payload": "{timestamp}{@api_key}5000{body}", "key_field": "api_secret",
                                            "headers": {"X-BAPI-API-KEY": "{@api_key}", "X-BAPI-TIMESTAMP": "{timestamp}", "X-BAPI-RECV-WINDOW": "5000", "X-BAPI-SIGN": "{signature}"}}},
                          "tools": {"cancel_order": {"method": "POST", "path": "/v5/order/cancel", "body": {"category": "=spot", "symbol": "symbol", "orderId": "order_id"}, "result": {"root": "result", "fields": {"order_id": "orderId", "status": "=cancelled"}}}}}}


@pytest.mark.asyncio
@respx.mock
async def test_hmac_signed_query_parameters():
    import hashlib, hmac
    route = respx.get(url__startswith="https://api.bnx.example/api/v3/account").mock(return_value=httpx.Response(200, json={"balances": [{"asset": "BTC", "free": "1.0"}]}))
    server = build_server(SIGN_BINANCE, transport=Transport("https://api.bnx.example", SIGN_BINANCE["adapter"]["auth"], {"api_key": "KEY-abcdef", "api_secret": "SECRET-abcdef"}, 50, "test"))
    res = await server.call_tool("get_balances", {})
    assert res.is_error is False
    req = route.calls[0].request
    query = req.url.query.decode()
    signed, _, sig = query.rpartition("&signature=")
    assert signed.startswith("omitZeroBalances=true&timestamp=")
    assert sig == hmac.new(b"SECRET-abcdef", signed.encode(), hashlib.sha256).hexdigest()
    assert req.headers["X-MBX-APIKEY"] == "KEY-abcdef"


@pytest.mark.asyncio
@respx.mock
async def test_hmac_signed_headers_over_the_exact_body_and_code_zero_envelope():
    import hashlib, hmac
    route = respx.post("https://api.byb.example/v5/order/cancel").mock(side_effect=[
        httpx.Response(200, json={"retCode": 0, "retMsg": "OK", "result": {"orderId": "o1"}}),
        httpx.Response(200, json={"retCode": 110001, "retMsg": "order not exists"})])
    server = build_server(SIGN_BYBIT, transport=Transport("https://api.byb.example", SIGN_BYBIT["adapter"]["auth"], {"api_key": "KEY-abcdef", "api_secret": "SECRET-abcdef"}, 50, "test", envelope=SIGN_BYBIT["adapter"]["envelope"]))
    ok = await server.call_tool("cancel_order", {"order_id": "o1", "symbol": "BTCUSDT"})
    assert ok.is_error is False and ok.structured_content["order_id"] == "o1"
    req = route.calls[0].request
    body = req.content.decode()
    ts = req.headers["X-BAPI-TIMESTAMP"]
    assert req.headers["X-BAPI-SIGN"] == hmac.new(b"SECRET-abcdef", f"{ts}KEY-abcdef5000{body}".encode(), hashlib.sha256).hexdigest()
    bad = await server.call_tool("cancel_order", {"order_id": "o2", "symbol": "BTCUSDT"})
    assert bad.is_error is True and "order not exists" in bad.content[0].text


@pytest.mark.asyncio
@respx.mock
async def test_session_login_with_get_query():
    spec = {"id": "wc", "category": "messaging", "label": "Wc", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://qy.example/cgi-bin", "rate_per_second": 50,
                        "auth": {"type": "session", "login": {"method": "GET", "path": "/gettoken", "body": {"corpid": "@corp_id", "corpsecret": "@corp_secret"}}, "token_path": "access_token",
                                 "header": "X-Unused", "fields": [{"name": "corp_id"}, {"name": "corp_secret"}]},
                        "tools": {"me": {"kind": "probe", "path": "/agent/list"}}}}
    login = respx.get("https://qy.example/cgi-bin/gettoken").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-wc", "expires_in": 7200}))
    respx.get("https://qy.example/cgi-bin/agent/list").mock(return_value=httpx.Response(200, json={"agentlist": []}))
    server = build_server(spec, transport=Transport(spec["adapter"]["base_url"], spec["adapter"]["auth"], {"corp_id": "CORP-1", "corp_secret": "CSECRET-1"}, 50, "test"))
    assert (await server.call_tool("me", {})).is_error is False
    assert dict(login.calls[0].request.url.params) == {"corpid": "CORP-1", "corpsecret": "CSECRET-1"}


@pytest.mark.asyncio
@respx.mock
async def test_unsigned_public_tool_and_decimal_strings():
    spec = json.loads(json.dumps(SIGN_BINANCE))
    spec["adapter"]["tools"]["get_ticker"] = {"path": "/api/v3/ticker/24hr", "sign": False, "params": {"symbol": "symbol"}, "result": {"fields": {"symbol": "symbol", "last": "lastPrice"}}}
    spec["adapter"]["tools"]["place_order"] = {"method": "POST", "path": "/api/v3/order", "params": {"symbol": "symbol", "quantity": "str:quantity"}, "result": {"fields": {"order_id": "orderId", "status": "=sent"}}}
    tick = respx.get(url__startswith="https://api.bnx.example/api/v3/ticker/24hr").mock(return_value=httpx.Response(200, json={"symbol": "BTCUSDT", "lastPrice": "1"}))
    order = respx.post(url__startswith="https://api.bnx.example/api/v3/order").mock(return_value=httpx.Response(200, json={"orderId": 5}))
    server = build_server(spec, transport=Transport("https://api.bnx.example", spec["adapter"]["auth"], {"api_key": "KEY-abcdef", "api_secret": "SECRET-abcdef"}, 50, "test"))
    assert (await server.call_tool("get_ticker", {"symbol": "BTCUSDT"})).is_error is False
    assert tick.calls[0].request.url.query.decode() == "symbol=BTCUSDT"
    await server.call_tool("place_order", {"symbol": "BTCUSDT", "side": "buy", "type": "market", "quantity": 0.00005})
    assert "quantity=0.00005&timestamp=" in order.calls[0].request.url.query.decode()


@pytest.mark.asyncio
@respx.mock
async def test_jsonstr_content_and_session_token_in_query():
    spec = {"id": "wc2", "category": "messaging", "label": "Wc2", "docs_url": "https://docs.example/", "verified_at": "2026-09-24",
            "adapter": {"base_url": "https://qy.example/cgi-bin", "rate_per_second": 50, "envelope": {"ok_field": "errcode", "ok_value": 0, "error_field": "errmsg"},
                        "auth": {"type": "session", "login": {"method": "GET", "path": "/gettoken", "body": {"corpid": "@corp_id", "corpsecret": "@corp_secret"}},
                                 "token_path": "access_token", "token_param": "access_token", "fields": [{"name": "corp_id"}, {"name": "corp_secret"}]},
                        "tools": {"send": {"method": "POST", "path": "/message/send", "body": {"touser": "to", "msgtype": "=text", "content": 'jsonstr:{"text": {text}}'},
                                           "result": {"fields": {"message_id": "msgid", "status": "=sent"}}}}}}
    respx.get("https://qy.example/cgi-bin/gettoken").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-wc2", "expires_in": 7200}))
    send = respx.post(url__startswith="https://qy.example/cgi-bin/message/send").mock(return_value=httpx.Response(200, json={"errcode": 0, "errmsg": "ok", "msgid": "m1"}))
    server = build_server(spec, transport=Transport(spec["adapter"]["base_url"], spec["adapter"]["auth"], {"corp_id": "CORP-1", "corp_secret": "CSECRET-1"}, 50, "test", envelope=spec["adapter"]["envelope"]))
    text = 'He said "hi"\nnext line \\ done'
    res = await server.call_tool("send", {"to": "u1", "text": text})
    assert res.is_error is False
    req = send.calls[0].request
    assert req.url.params["access_token"] == "ACCESS-wc2" and "Authorization" not in req.headers
    body = json.loads(req.content)
    assert isinstance(body["content"], str) and json.loads(body["content"]) == {"text": text}


@pytest.mark.asyncio
@respx.mock
async def test_map_to_typed_boolean():
    spec = {"id": "ob", "category": "ads", "label": "Ob", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
            "adapter": {"base_url": "https://ob.example", "rate_per_second": 50, "auth": {"type": "none", "fields": []},
                        "tools": {"pause_resume": {"method": "PUT", "path": "/campaigns/{campaign_id}", "body": {"enabled": "map:action:pause=json:false,resume=json:true"}, "result": {"fields": {"campaign_id": "id", "status": "=updated"}}}}}}
    route = respx.put("https://ob.example/campaigns/7").mock(return_value=httpx.Response(200, json={"id": "7"}))
    server = build_server(spec, transport=Transport("https://ob.example", spec["adapter"]["auth"], {}, 50, "test"))
    assert (await server.call_tool("pause_resume", {"campaign_id": "7", "action": "pause"})).is_error is False
    assert json.loads(route.calls[0].request.content) == {"enabled": False}


# ---- 2026-09-25 runtime features: dates, money, dynamic keys, keyed lists, cursors, XML, token options, signing modes

WAVE = {"id": "wv", "category": "ecommerce_channels", "label": "Wv", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
        "adapter": {"base_url": "https://wv.example", "rate_per_second": 50, "auth": {"type": "none", "fields": []},
                    "tools": {
                        "list_orders": {"path": "/orders", "params": {"from": "epoch:since", "from_ms": "epoch_ms:since", "d": "datefmt:%m/%d/%Y:since", "to": "days_ahead:0", "after": "cursor"},
                                        "result": {"items": "data.orders", "items_are_values": True, "key": "orders", "next_cursor": "data.next", "fields": {"order_id": "_key", "status": "st"}}},
                        "update_listing": {"method": "PUT", "path": "/items", "body": {"updates.{listing_id}.price_cents": "minor:price", "updates.{listing_id}.budget_micros": "micros:price", "k": "mul:1000:price"},
                                           "result": {"fields": {"listing_id": "=ok", "status": "=updated"}}},
                        "set_inventory": {"method": "POST", "path": "/stock", "body_format": "xml", "xml_root": "Request", "body": {"Product.SellerSku": "sku", "Product.Quantity": "quantity", "Product.@op": "=set"},
                                          "result": {"root": "Response.Head", "fields": {"listing_id": "RequestId", "status": "Status"}}}}}}


def _wv():
    return build_server(WAVE, transport=Transport("https://wv.example", WAVE["adapter"]["auth"], {}, 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_dates_cursor_and_keyed_lists():
    route = respx.get(url__startswith="https://wv.example/orders").mock(return_value=httpx.Response(200, json={"data": {"orders": {"A1": {"st": "new"}, "A2": {"st": "paid"}}, "next": "tok2"}}))
    res = await _wv().call_tool("list_orders", {"since": "2026-09-01", "cursor": "tok1"})
    sc = res.structured_content
    assert res.is_error is False and [o["order_id"] for o in sc["orders"]] == ["A1", "A2"] and sc["next_cursor"] == "tok2"
    q = route.calls[0].request.url.params
    assert q["from"] == "1788220800" and q["from_ms"] == "1788220800000" and q["d"] == "09/01/2026" and q["after"] == "tok1"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", q["to"])


@pytest.mark.asyncio
@respx.mock
async def test_money_units_and_dynamic_body_keys():
    route = respx.put("https://wv.example/items").mock(return_value=httpx.Response(204))
    assert (await _wv().call_tool("update_listing", {"listing_id": "SKU-9", "price": 19.995})).is_error is False
    assert json.loads(route.calls[0].request.content) == {"updates": {"SKU-9": {"price_cents": 2000, "budget_micros": 19995000}}, "k": 19995}


@pytest.mark.asyncio
@respx.mock
async def test_xml_request_and_response():
    route = respx.post("https://wv.example/stock").mock(return_value=httpx.Response(200, headers={"content-type": "application/xml"},
        text='<?xml version="1.0"?><Response><Head><RequestId>r-1</RequestId><Status>ok</Status></Head></Response>'))
    res = await _wv().call_tool("set_inventory", {"sku": "S&1", "quantity": 4})
    assert res.is_error is False and res.structured_content["listing_id"] == "r-1" and res.structured_content["status"] == "ok"
    body = route.calls[0].request.content.decode()
    assert body == '<?xml version="1.0" encoding="UTF-8"?><Request><Product op="set"><SellerSku>S&amp;1</SellerSku><Quantity>4</Quantity></Product></Request>'
    assert route.calls[0].request.headers["Content-Type"] == "application/xml"


@pytest.mark.asyncio
@respx.mock
async def test_token_url_placeholder_get_method_headers_and_header_token():
    spec = {"id": "tk", "category": "messaging", "label": "Tk", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
            "adapter": {"base_url": "https://{region}.tk.example", "rate_per_second": 50,
                        "auth": {"type": "oauth2_client_credentials", "token_url": "https://{region}.tk.example/token", "token_method": "GET", "client_auth": "body",
                                 "token_headers": {"WM_SVC.NAME": "platform-mcp", "X-Key": "{@client_id}"}, "fields": [{"name": "client_id"}, {"name": "client_secret"}]},
                        "config_fields": [{"name": "region"}],
                        "tools": {"me": {"kind": "probe", "path": "/me"}}}}
    tok = respx.get(url__startswith="https://eu.tk.example/token").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-tk", "expires_in": 900}))
    me = respx.get("https://eu.tk.example/me").mock(return_value=httpx.Response(200, json={"id": 1}))
    server = build_server(spec, transport=Transport(spec["adapter"]["base_url"], spec["adapter"]["auth"], {"client_id": "CID-1", "client_secret": "SECRET-tk", "region": "eu"}, 50, "test"))
    assert (await server.call_tool("me", {})).is_error is False
    req = tok.calls[0].request
    assert req.url.params["grant_type"] == "client_credentials" and req.url.params["client_id"] == "CID-1"
    assert req.headers["WM_SVC.NAME"] == "platform-mcp" and req.headers["X-Key"] == "CID-1"
    assert me.calls[0].request.headers["Authorization"] == "Bearer ACCESS-tk"
    s2 = json.loads(json.dumps(spec)); s2["adapter"]["auth"] = {"type": "session", "login": {"method": "POST", "path": "/login", "body": {"auth.user": "@user", "auth.pass": "@password"}, "headers": {"X-App": "{@app}"}},
                                                                "token_from_header": "X-Auth-Token", "prefix": "", "header": "X-Auth-Token", "fields": [{"name": "user"}, {"name": "password"}]}
    login = respx.post("https://eu.tk.example/login").mock(return_value=httpx.Response(204, headers={"X-Auth-Token": "SESSION-tk"}))
    server2 = build_server(s2, transport=Transport(s2["adapter"]["base_url"], s2["adapter"]["auth"], {"user": "u", "password": "PASSWORD-tk", "region": "eu", "app": "APP-1"}, 50, "test"))
    assert (await server2.call_tool("me", {})).is_error is False
    assert json.loads(login.calls[0].request.content) == {"auth": {"user": "u", "pass": "PASSWORD-tk"}} and login.calls[0].request.headers["X-App"] == "APP-1"
    assert me.calls[-1].request.headers["X-Auth-Token"] == "SESSION-tk"


@pytest.mark.asyncio
@respx.mock
async def test_signing_modes_hash_upper_sorted_and_jwt():
    import hashlib
    import jwt as pyjwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    spec = {"id": "sg", "category": "ecommerce_channels", "label": "Sg", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
            "adapter": {"base_url": "https://sg.example", "rate_per_second": 50,
                        "auth": {"type": "none", "fields": [{"name": "app_key"}, {"name": "app_secret"}],
                                 "sign": {"mode": "hash", "algorithm": "md5", "case": "upper", "payload": "{@app_secret}{sorted_params}{@app_secret}", "timestamp_param": "timestamp", "params": {"app_key": "{@app_key}"}, "signature_param": "sign"}},
                        "tools": {"list_orders": {"path": "/orders", "params": {"status": "status"}, "result": {"items": "orders", "key": "orders", "fields": {"order_id": "id"}}}}}}
    route = respx.get(url__startswith="https://sg.example/orders").mock(return_value=httpx.Response(200, json={"orders": [{"id": 1}]}))
    server = build_server(spec, transport=Transport("https://sg.example", spec["adapter"]["auth"], {"app_key": "KEY-sg", "app_secret": "SECRET-sg"}, 50, "test"))
    assert (await server.call_tool("list_orders", {"status": "paid"})).is_error is False
    params = dict(route.calls[0].request.url.params)
    sig = params.pop("sign")
    assert sig == hashlib.md5(("SECRET-sg" + "".join(k + v for k, v in sorted(params.items())) + "SECRET-sg").encode()).hexdigest().upper()
    # JWT HS256 and RS256 bearer assertions
    for mode in ("jwt_hs256", "jwt_rs256"):
        if mode == "jwt_hs256":
            secret, verify = "SECRET-jwt-0123456789-abcdefghijklmnop", "SECRET-jwt-0123456789-abcdefghijklmnop"
        else:
            k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            secret = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
            verify = k.public_key()
        s3 = json.loads(json.dumps(spec)); s3["adapter"]["auth"] = {"type": "none", "fields": [{"name": "api_key"}, {"name": "api_secret"}],
            "sign": {"mode": mode, "key_field": "api_secret", "claims": {"iss": "{@api_key}", "iat": "{timestamp_s}", "exp": "+300"}, "jwt_header": {"kid": "k1"}, "headers": {"Authorization": "Bearer {signature}"}}}
        r3 = respx.get(url__startswith="https://sg.example/orders").mock(return_value=httpx.Response(200, json={"orders": []}))
        sv = build_server(s3, transport=Transport("https://sg.example", s3["adapter"]["auth"], {"api_key": "KEY-jwt", "api_secret": secret}, 50, "test"))
        assert (await sv.call_tool("list_orders", {})).is_error is False
        token = r3.calls[-1].request.headers["Authorization"].split(" ", 1)[1]
        claims = pyjwt.decode(token, verify, algorithms=["HS256" if mode == "jwt_hs256" else "RS256"])
        assert claims["iss"] == "KEY-jwt" and claims["exp"] - claims["iat"] == 300 and pyjwt.get_unverified_header(token)["kid"] == "k1"


# ---- 2026-09-25 (2): signing variants, AWS SigV4, OAuth 1.0a, body-field signatures, token field renames

def _sg(auth, tools=None, creds=None, base="https://api.sg2.example"):
    spec = {"id": "sg2", "category": "ecommerce_channels", "label": "Sg2", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
            "adapter": {"base_url": base, "rate_per_second": 50, "auth": auth,
                        "tools": tools or {"list_orders": {"path": "/rest/orders/get", "params": {"status": "status"}, "result": {"items": "orders", "key": "orders", "fields": {"order_id": "id"}}}}}}
    return build_server(spec, transport=Transport(base, auth, creds or {}, 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_timezone_timestamp_path_strip_sorted_forms_and_pre_digest(monkeypatch):
    import hashlib, hmac, time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.get(url__startswith="https://api.sg2.example/rest/orders/get").mock(return_value=httpx.Response(200, json={"orders": []}))
    auth = {"type": "none", "fields": [{"name": "app_key"}, {"name": "app_secret"}],
            "sign": {"mode": "hmac", "algorithm": "sha256", "case": "upper", "key_field": "app_secret", "path_strip": "/rest",
                     "timestamp_param": "timestamp", "timestamp_value": "timestamp_fmt", "timestamp_format": "%Y-%m-%d %H:%M:%S", "timestamp_offset": "+08:00",
                     "params": {"app_key": "{@app_key}"}, "payload": "{path}{sorted_params}|{sorted_values}|{sorted_kv}",
                     "pre": [{"name": "ts_md5", "mode": "hash", "algorithm": "md5", "payload": "{timestamp_s}"}],
                     "headers": {"token": "{ts_md5}"}, "signature_param": "sign"}}
    assert (await _sg(auth, creds={"app_key": "KEY-1", "app_secret": "SECRET-1"}).call_tool("list_orders", {"status": "paid"})).is_error is False
    req = route.calls[0].request
    q = dict(req.url.params); sig = q.pop("sign")
    from datetime import datetime, timedelta, timezone
    assert q["timestamp"] == (datetime.fromtimestamp(1790301600, timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    kv = sorted(q.items())
    payload = "/orders/get" + "".join(k + v for k, v in kv) + "|" + "".join(v for _, v in kv) + "|" + "".join(f"{k}={v}" for k, v in kv)
    assert sig == hmac.new(b"SECRET-1", payload.encode(), hashlib.sha256).hexdigest().upper()
    assert req.headers["token"] == hashlib.md5(b"1790301600").hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_aws_sigv4_matches_the_aws_test_suite_vector(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1440938160.0)  # 20150830T123600Z (AWS "get-vanilla")
    route = respx.get("https://example.amazonaws.com/").mock(return_value=httpx.Response(200, json={}))
    auth = {"type": "none", "fields": [{"name": "access_key_id"}, {"name": "secret_access_key"}], "sign": {"mode": "aws_sigv4", "service": "service", "region": "us-east-1"}}
    server = _sg(auth, tools={"me": {"kind": "probe", "path": "/"}}, creds={"access_key_id": "AKIDEXAMPLE", "secret_access_key": "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"}, base="https://example.amazonaws.com")
    assert (await server.call_tool("me", {})).is_error is False
    h = route.calls[0].request.headers
    assert h["X-Amz-Date"] == "20150830T123600Z"
    assert h["Authorization"] == "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20150830/us-east-1/service/aws4_request, SignedHeaders=host;x-amz-date, Signature=5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31"


@pytest.mark.asyncio
@respx.mock
async def test_oauth1_hmac_sha1_signature():
    import base64 as b64, hashlib, hmac
    from urllib.parse import quote
    route = respx.get(url__startswith="https://api.sg2.example/rest/orders/get").mock(return_value=httpx.Response(200, json={"orders": []}))
    auth = {"type": "none", "fields": [{"name": "consumer_key"}, {"name": "consumer_secret"}, {"name": "access_token"}, {"name": "access_token_secret"}], "sign": {"mode": "oauth1"}}
    creds = {"consumer_key": "CK-1", "consumer_secret": "CS-1&x", "access_token": "AT-1", "access_token_secret": "ATS-1"}
    assert (await _sg(auth, creds=creds).call_tool("list_orders", {"status": "a b"})).is_error is False
    hdr = route.calls[0].request.headers["Authorization"]
    oauth = dict(x.split("=", 1) for x in hdr[len("OAuth "):].split(", "))
    oauth = {k: v.strip('"') for k, v in oauth.items()}
    from urllib.parse import unquote
    sig = unquote(oauth.pop("oauth_signature"))
    enc = lambda x: quote(str(x), safe="-._~")
    params = sorted([(enc("status"), enc("a b"))] + [(k, v) for k, v in oauth.items()])
    base = "&".join(["GET", enc("https://api.sg2.example/rest/orders/get"), enc("&".join(f"{k}={v}" for k, v in params))])
    key = f"{enc('CS-1&x')}&{enc('ATS-1')}"
    assert sig == b64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()


@pytest.mark.asyncio
@respx.mock
async def test_body_field_signature_rsa_and_jwt_key_decoding():
    import base64 as b64, hashlib
    import jwt as pyjwt
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    route = respx.post("https://api.sg2.example/api").mock(return_value=httpx.Response(200, json={"ok": True}))
    tools = {"update_listing": {"method": "POST", "path": "/api", "body": {"type": "=bg.goods.update", "goods_id": "listing_id", "price": "str:price"}, "result": {"fields": {"listing_id": "=x", "status": "=updated"}}}}
    auth = {"type": "none", "fields": [{"name": "app_secret"}], "sign": {"mode": "hash", "algorithm": "md5", "case": "upper", "payload": "{@app_secret}{sorted_body}{@app_secret}", "body_field": "sign"}}
    assert (await _sg(auth, tools=tools, creds={"app_secret": "SECRET-t"}).call_tool("update_listing", {"listing_id": "G1", "price": 9.5})).is_error is False
    body = json.loads(route.calls[0].request.content); sig = body.pop("sign")
    assert sig == hashlib.md5(("SECRET-t" + "".join(k + str(v) for k, v in sorted(body.items())) + "SECRET-t").encode()).hexdigest().upper()
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    auth2 = {"type": "none", "fields": [{"name": "private_key"}], "sign": {"mode": "rsa_sha256", "payload": "{method}\n{path}\n{timestamp}", "headers": {"X-Sig": "{signature}", "X-Ts": "{timestamp}"}}}
    r2 = respx.get(url__startswith="https://api.sg2.example/rest/orders/get").mock(return_value=httpx.Response(200, json={"orders": []}))
    assert (await _sg(auth2, creds={"private_key": pem}).call_tool("list_orders", {})).is_error is False
    h = r2.calls[-1].request.headers
    k.public_key().verify(b64.b64decode(h["X-Sig"]), f"GET\n/rest/orders/get\n{h['X-Ts']}".encode(), padding.PKCS1v15(), hashes.SHA256())
    raw_secret = b"\x01\x02binary-secret-0123456789abcdefghij"
    auth3 = {"type": "none", "fields": [{"name": "api_secret"}, {"name": "kid"}], "sign": {"mode": "jwt_hs256", "key_encoding": "base64url", "claims": {"iss": "dev"}, "jwt_header": {"kid": "{@kid}"}, "headers": {"Authorization": "Bearer {signature}"}}}
    creds3 = {"api_secret": b64.urlsafe_b64encode(raw_secret).decode().rstrip("="), "kid": "KID-7"}
    assert (await _sg(auth3, creds=creds3).call_tool("list_orders", {})).is_error is False
    tok = r2.calls[-1].request.headers["Authorization"].split(" ")[1]
    assert pyjwt.decode(tok, raw_secret, algorithms=["HS256"])["iss"] == "dev" and pyjwt.get_unverified_header(tok)["kid"] == "KID-7"


@pytest.mark.asyncio
@respx.mock
async def test_token_field_renames_and_nested_rotation(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    tok = respx.post("https://ad.example/oauth2/refresh_token").mock(return_value=httpx.Response(200, json={"code": 0, "data": {"access_token": "ACCESS-oe", "refresh_token": "REFRESH-oe-2", "expires_in": 86400}}))
    me = respx.get("https://ad.example/me").mock(return_value=httpx.Response(200, json={"id": 1}))
    auth = {"type": "oauth2_refresh_token", "token_url": "https://ad.example/oauth2/refresh_token", "client_auth": "body", "token_body": "json", "state_key": "oe",
            "token_fields": {"client_id": "app_id", "client_secret": "secret", "grant_type": None}, "token_path": "data.access_token", "refresh_token_path": "data.refresh_token",
            "expires_path": "data.expires_in", "header": "Access-Token", "prefix": "", "fields": [{"name": "client_id"}, {"name": "client_secret"}, {"name": "refresh_token"}]}
    server = _sg(auth, tools={"me": {"kind": "probe", "path": "/me"}}, creds={"client_id": "APP-1", "client_secret": "SECRET-oe", "refresh_token": "REFRESH-oe-1"}, base="https://ad.example")
    assert (await server.call_tool("me", {})).is_error is False
    assert json.loads(tok.calls[0].request.content) == {"refresh_token": "REFRESH-oe-1", "app_id": "APP-1", "secret": "SECRET-oe"}
    assert me.calls[0].request.headers["Access-Token"] == "ACCESS-oe"
    assert json.loads((tmp_path / "oe.json").read_text())["refresh_token"] == "REFRESH-oe-2"


# ---- 2026-09-25 (3): multipart uploads, cookie sessions, signed token requests, cookie-returned tokens

@pytest.mark.asyncio
@respx.mock
async def test_multipart_with_downloaded_file_and_cookie_session():
    img = respx.get("https://93.184.215.14/cat.png", headers={"host": "cdn.example"}).mock(return_value=httpx.Response(200, content=b"\x89PNGDATA", headers={"content-type": "image/png"}))
    gen = respx.post("https://mp.example/v2/generate").mock(return_value=httpx.Response(200, json={"id": "j1", "status": "queued"}))
    auth = {"type": "session", "login": {"method": "POST", "path": "/login", "body": {"u": "@user", "p": "@password"}}, "token_from_cookie": "SESSION",
            "header": "", "cookies": {"SESSION": "{access_token}", "uid": "{nonce}"}, "fields": [{"name": "user"}, {"name": "password"}]}
    login = respx.post("https://mp.example/login").mock(return_value=httpx.Response(200, json={"ok": True}, headers={"set-cookie": "SESSION=SESS-mp; Path=/; HttpOnly"}))
    spec = {"id": "mp", "category": "builder_tools", "label": "Mp", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
            "adapter": {"base_url": "https://mp.example", "rate_per_second": 50, "auth": auth,
                        "tools": {"generate_image": {"method": "POST", "path": "/v2/generate", "body_format": "multipart", "body": {"prompt": "prompt", "image": "file:image_url", "output_format": "=png"},
                                                     "result": {"fields": {"job_id": "id", "status": "status"}}}}}}
    t = Transport("https://mp.example", auth, {"user": "u", "password": "PASSWORD-mp"}, 50, "test")

    async def public(host):  # the download guard resolves the host (netguard.py); cdn.example is public here
        return ["93.184.215.14"]
    t.resolve_host = public
    server = build_server(spec, transport=t)
    res = await server.call_tool("generate_image", {"prompt": "a cat", "image_url": "https://cdn.example/cat.png"})
    assert res.is_error is False and res.structured_content["job_id"] == "j1" and login.called and img.called
    req = gen.calls[0].request
    ct = req.headers["content-type"]; assert ct.startswith("multipart/form-data; boundary=")
    body = req.content
    assert b'name="prompt"\r\n\r\na cat' in body and b'name="image"; filename="cat.png"' in body and b"\x89PNGDATA" in body and b'name="output_format"\r\n\r\npng' in body
    cookie = req.headers["Cookie"]; assert cookie.startswith("SESSION=SESS-mp; uid=") and "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_signed_token_refresh_and_token_in_request_signature(monkeypatch):
    import hashlib, hmac, time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    tok = respx.post(url__startswith="https://partner.shopee.example/api/v2/auth/access_token/get").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-sp", "refresh_token": "REFRESH-sp-2", "expire_in": 14400}))
    api = respx.get(url__startswith="https://partner.shopee.example/api/v2/order/get_order_list").mock(return_value=httpx.Response(200, json={"response": {"order_list": []}}))
    auth = {"type": "oauth2_refresh_token", "token_url": "https://partner.shopee.example/api/v2/auth/access_token/get", "token_body": "json", "client_auth": "body",
            "token_fields": {"client_id": None, "client_secret": None, "grant_type": None}, "expires_path": "expire_in", "header": "", "token_param": "access_token",
            "token_sign": {"mode": "hmac", "algorithm": "sha256", "key_field": "partner_key", "payload": "{@partner_id}{path}{timestamp_s}"},
            "token_query": {"partner_id": "{@partner_id}", "timestamp": "{timestamp_s}", "sign": "{signature}"},
            "token_body_extra": {"partner_id": "int:{@partner_id}", "shop_id": "int:{@shop_id}"},
            "sign": {"mode": "hmac", "algorithm": "sha256", "key_field": "partner_key", "payload": "{@partner_id}{path}{timestamp_s}{access_token}{@shop_id}",
                     "params": {"partner_id": "{@partner_id}", "shop_id": "{@shop_id}", "timestamp": "{timestamp_s}"}, "signature_param": "sign"},
            "fields": [{"name": "client_id", "required": False}, {"name": "refresh_token"}, {"name": "partner_key"}]}
    spec = {"id": "sp", "category": "ecommerce_channels", "label": "Sp", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
            "adapter": {"base_url": "https://partner.shopee.example", "rate_per_second": 50, "auth": auth,
                        "tools": {"list_orders": {"path": "/api/v2/order/get_order_list", "result": {"items": "response.order_list", "key": "orders", "fields": {"order_id": "order_sn"}}}}}}
    creds = {"client_id": "x", "refresh_token": "REFRESH-sp-1", "partner_key": "PKEY-sp", "partner_id": "1001", "shop_id": "2002"}
    server = build_server(spec, transport=Transport(spec["adapter"]["base_url"], auth, creds, 50, "test"))
    assert (await server.call_tool("list_orders", {})).is_error is False
    t = tok.calls[0].request
    assert json.loads(t.content) == {"refresh_token": "REFRESH-sp-1", "partner_id": 1001, "shop_id": 2002}
    assert t.url.params["sign"] == hmac.new(b"PKEY-sp", b"1001/api/v2/auth/access_token/get1790301600", hashlib.sha256).hexdigest()
    q = api.calls[0].request.url.params
    assert q["access_token"] == "ACCESS-sp" and q["sign"] == hmac.new(b"PKEY-sp", b"1001/api/v2/order/get_order_list1790301600ACCESS-sp2002", hashlib.sha256).hexdigest()


# ---- 2026-09-25 (4): token in path/body, several ok values, CSV, JSON multipart parts, client assertions, cookie replay, sign exclusions

@pytest.mark.asyncio
@respx.mock
async def test_token_placement_ok_values_csv_jsonpart_and_exclusions(monkeypatch):
    import hashlib
    login = respx.post("https://t4.example/api/login").mock(return_value=httpx.Response(200, json={"Token": "TOK-4"}, headers={"set-cookie": "a=1; Path=/"}))
    path_call = respx.get("https://t4.example/api/stock/TOK-4").mock(return_value=httpx.Response(200, json={"code": "200", "stock": []}))
    body_call = respx.post("https://t4.example/api/report").mock(return_value=httpx.Response(200, json={"code": 200, "data": {"id": "r1"}}))
    bad = respx.post("https://t4.example/api/fail").mock(return_value=httpx.Response(200, json={"code": 500, "msg": "boom"}))
    csv_call = respx.get("https://t4.example/api/tenders.csv").mock(return_value=httpx.Response(200, headers={"content-type": "text/csv; charset=utf-8"}, text='﻿id,title\n1,"Roads, bridges"\n2,Water\n'))
    mp = respx.post("https://t4.example/api/search").mock(return_value=httpx.Response(200, json={"code": 200, "results": []}))
    auth = {"type": "session", "login": {"method": "POST", "path": "/api/login", "body": {"User": "@user", "Password": "@password"}}, "token_path": "Token", "header": "",
            "token_body_path": "header.accessToken", "fields": [{"name": "user"}, {"name": "password"}]}
    spec = {"id": "t4", "category": "deals", "label": "T4", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
            "adapter": {"base_url": "https://t4.example", "rate_per_second": 50, "auth": auth, "envelope": {"ok_field": "code", "ok_value": ["200", 200], "error_field": "msg"},
                        "tools": {"me": {"kind": "probe", "path": "/api/stock/{access_token}"},
                                  "get_posting": {"method": "POST", "path": "/api/report", "body": {"body.id": "id"}, "result": {"root": "data", "fields": {"id": "id"}}},
                                  "bid_status": {"method": "POST", "path": "/api/fail", "body": {"x": "=1"}, "result": {"fields": {"bid_id": "id"}}},
                                  "search_postings": {"path": "/api/tenders.csv", "result": {"items": "rows", "key": "postings", "fields": {"id": "id", "title": "title"}}},
                                  "list_messages": {"method": "POST", "path": "/api/search", "body_format": "multipart", "body": {"query": "jsonpart:json:{\"bool\":{\"must\":[]}}", "text": "=*"}, "result": {"items": "results", "key": "messages", "fields": {"id": "id"}}}}}}
    t = Transport(spec["adapter"]["base_url"], auth, {"user": "u", "password": "PASSWORD-4"}, 50, "test", envelope=spec["adapter"]["envelope"])
    server = build_server(spec, transport=t)
    assert (await server.call_tool("me", {})).is_error is False and path_call.called
    assert (await server.call_tool("get_posting", {"id": "p9"})).is_error is False
    assert json.loads(body_call.calls[0].request.content) == {"body": {"id": "p9"}, "header": {"accessToken": "TOK-4"}}
    assert (await server.call_tool("bid_status", {"bid_id": "b"})).is_error is True
    res = await server.call_tool("search_postings", {"query": "x"})
    assert [p["title"] for p in res.structured_content["postings"]] == ["Roads, bridges", "Water"]
    assert (await server.call_tool("list_messages", {})).is_error is False
    raw = mp.calls[0].request.content
    assert b'name="query"\r\nContent-Type: application/json\r\n\r\n{"bool": {"must": []}}' in raw or b'name="query"\r\nContent-Type: application/json\r\n\r\n{"bool":{"must":[]}}' in raw
    # sign exclusions
    sg = {"type": "none", "fields": [{"name": "app_secret"}], "sign": {"mode": "hash", "algorithm": "md5", "payload": "{@app_secret}{sorted_params}{@app_secret}", "params": {"access_token": "AT", "sign_method": "md5", "app_key": "K"}, "exclude": ["access_token", "sign_method"], "signature_param": "sign"}}
    r2 = respx.get(url__startswith="https://t5.example/orders").mock(return_value=httpx.Response(200, json={"orders": []}))
    spec2 = {"id": "t5", "category": "deals", "label": "T5", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
             "adapter": {"base_url": "https://t5.example", "rate_per_second": 50, "auth": sg, "tools": {"search_postings": {"path": "/orders", "result": {"items": "orders", "key": "postings", "fields": {"id": "id"}}}}}}
    assert (await build_server(spec2, transport=Transport("https://t5.example", sg, {"app_secret": "S5"}, 50, "test")).call_tool("search_postings", {"query": "q"})).is_error is False
    q = r2.calls[0].request.url.params
    assert q["sign"] == hashlib.md5(b"S5app_keyKS5").hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_jwt_client_assertion_in_token_request_and_all_cookie_replay():
    import jwt as pyjwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    tok = respx.post("https://id.example/oauth2/token").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-ca", "expires_in": 600}))
    me = respx.get("https://dsp.example/me").mock(return_value=httpx.Response(200, json={"id": 1}))
    auth = {"type": "oauth2_client_credentials", "token_url": "https://id.example/oauth2/token", "client_auth": "body",
            "token_jwt": {"mode": "jwt_rs256", "key_field": "private_key", "claims": {"iss": "{@client_id}", "sub": "{@client_id}", "aud": "https://id.example/oauth2/token", "exp": "+600", "jti": "{nonce}"}, "jwt_header": {"kid": "{@kid}"}},
            "token_fields": {"client_secret": None},
            "token_params": {"client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer", "client_assertion": "{client_assertion}"},
            "fields": [{"name": "client_id"}, {"name": "private_key"}, {"name": "kid"}]}
    spec = {"id": "ca", "category": "ads", "label": "Ca", "docs_url": "https://docs.example/", "verified_at": "2026-09-25",
            "adapter": {"base_url": "https://dsp.example", "rate_per_second": 50, "auth": auth, "tools": {"me": {"kind": "probe", "path": "/me"}}}}
    server = build_server(spec, transport=Transport("https://dsp.example", auth, {"client_id": "CID-ca", "private_key": pem, "kid": "k9"}, 50, "test"))
    assert (await server.call_tool("me", {})).is_error is False
    form = dict(x.split("=", 1) for x in tok.calls[0].request.content.decode().split("&"))
    from urllib.parse import unquote
    assertion = unquote(form["client_assertion"])
    claims = pyjwt.decode(assertion, k.public_key(), algorithms=["RS256"], audience="https://id.example/oauth2/token")
    assert claims["iss"] == "CID-ca" and pyjwt.get_unverified_header(assertion)["kid"] == "k9" and "client_secret" not in form
    assert me.calls[0].request.headers["Authorization"] == "Bearer ACCESS-ca"
    # all login cookies replayed
    login = respx.post("https://noon.example/login").mock(return_value=httpx.Response(200, json={}, headers=[("set-cookie", "a=1; Path=/"), ("set-cookie", "b=2; Path=/")]))
    call = respx.get("https://noon.example/me").mock(return_value=httpx.Response(200, json={"id": 1}))
    a2 = {"type": "session", "login": {"method": "POST", "path": "/login", "body": {"token": "{client_assertion}"}}, "token_from_cookie": "*", "header": "",
          "token_jwt": {"mode": "jwt_rs256", "key_field": "private_key", "claims": {"sub": "{@client_id}", "iat": "{timestamp_s}"}}, "fields": [{"name": "client_id"}, {"name": "private_key"}]}
    spec2 = {**spec, "adapter": {**spec["adapter"], "base_url": "https://noon.example", "auth": a2}}
    s2 = build_server(spec2, transport=Transport("https://noon.example", a2, {"client_id": "CID-n", "private_key": pem}, 50, "test"))
    assert (await s2.call_tool("me", {})).is_error is False
    sent = json.loads(login.calls[0].request.content)["token"]
    assert pyjwt.decode(sent, k.public_key(), algorithms=["RS256"])["sub"] == "CID-n"
    assert call.calls[0].request.headers["Cookie"] == "a=1; b=2"
