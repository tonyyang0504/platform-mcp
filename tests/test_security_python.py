"""Security review 2026-10 (docs/SECURITY_REVIEW_2026-10.md): regression tests for the Python runtime.
tests/security.typescript.test.mjs checks the same cases against the TypeScript runtime."""
import base64
import json
import os
import stat
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub import credentials, netguard  # noqa: E402
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

CASES = json.loads((ROOT / "tests" / "fixtures" / "netguard_cases.json").read_text(encoding="utf-8"))
PUBLIC = "93.184.215.14"


async def public_resolver(host: str) -> list[str]:
    return [PUBLIC]


# ---------------------------------------------------------------- SR-02: SSRF through multipart file: downloads

def test_netguard_ip_table():
    for ip, public in CASES["ips"].items():
        assert netguard.is_public_ip(ip) is public, ip


@pytest.mark.asyncio
async def test_netguard_url_cases(monkeypatch):
    monkeypatch.delenv(netguard.ALLOW_ENV, raising=False)
    for case in CASES["urls"]:
        async def resolver(host, answer=case["resolves"]):
            return list(answer)
        try:
            await netguard.check_url(case["url"], resolver)
            ok = True
        except Exception as exc:
            assert exc.__class__.__name__ == "InvalidInput", exc
            ok = False
        assert ok is case["ok"], case["url"]
    monkeypatch.setenv(netguard.ALLOW_ENV, "1")
    await netguard.check_url("http://169.254.169.254/", public_resolver)  # the operator's explicit opt-out


MP_SPEC = {"id": "mpx", "category": "builder_tools", "label": "Mpx", "docs_url": "https://docs.example/", "verified_at": "2026-10-01",
           "adapter": {"base_url": "https://mp.example", "rate_per_second": 50, "auth": {"type": "bearer", "field": "token", "fields": [{"name": "token"}]},
                       "tools": {"generate_image": {"method": "POST", "path": "/v2/generate", "body_format": "multipart",
                                                    "body": {"prompt": "prompt", "image": "file:image_url"}, "result": {"fields": {"job_id": "id", "status": "status"}}}}}}


def _mp_server(resolver=public_resolver):
    t = Transport("https://mp.example", MP_SPEC["adapter"]["auth"], {"token": "TOKEN-mpx-123"}, 50, "test")
    t.resolve_host = resolver
    return build_server(MP_SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_file_download_refuses_metadata_and_private_hosts(monkeypatch):
    monkeypatch.delenv(netguard.ALLOW_ENV, raising=False)
    meta = respx.get(url__startswith="http://169.254.169.254/").mock(return_value=httpx.Response(200, text="AKIA-SECRET"))
    gen = respx.post("https://mp.example/v2/generate").mock(return_value=httpx.Response(200, json={"id": "j1", "status": "queued"}))
    res = await _mp_server().call_tool("generate_image", {"prompt": "x", "image_url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/role"})
    assert res.is_error and res.structured_content["error"] == "invalid_input"
    assert not meta.called and not gen.called

    async def internal(host):
        return ["10.0.0.7"]
    internal_route = respx.get("https://intranet.example/secret.png").mock(return_value=httpx.Response(200, content=b"x"))
    res = await _mp_server(internal).call_tool("generate_image", {"prompt": "x", "image_url": "https://intranet.example/secret.png"})
    assert res.is_error and not internal_route.called and not gen.called


@pytest.mark.asyncio
@respx.mock
async def test_file_download_rechecks_every_redirect(monkeypatch):
    monkeypatch.delenv(netguard.ALLOW_ENV, raising=False)
    respx.get("https://93.184.215.14/a.png", headers={"host": "cdn.example"}).mock(return_value=httpx.Response(302, headers={"location": "http://127.0.0.1:8080/admin"}))
    local = respx.get("http://127.0.0.1:8080/admin").mock(return_value=httpx.Response(200, content=b"admin"))
    gen = respx.post("https://mp.example/v2/generate").mock(return_value=httpx.Response(200, json={"id": "j1", "status": "queued"}))
    res = await _mp_server().call_tool("generate_image", {"prompt": "x", "image_url": "https://cdn.example/a.png"})
    assert res.is_error and not local.called and not gen.called
    # a redirect to another public host is followed and checked
    respx.get("https://93.184.215.14/b.png", headers={"host": "cdn.example"}).mock(return_value=httpx.Response(301, headers={"location": "https://cdn2.example/b.png"}))
    respx.get("https://93.184.215.14/b.png", headers={"host": "cdn2.example"}).mock(return_value=httpx.Response(200, content=b"PNG", headers={"content-type": "image/png"}))
    res = await _mp_server().call_tool("generate_image", {"prompt": "x", "image_url": "https://cdn.example/b.png"})
    assert res.is_error is False and gen.called and b"PNG" in gen.calls.last.request.content


@pytest.mark.asyncio
@respx.mock
async def test_file_download_size_cap(monkeypatch):
    monkeypatch.delenv(netguard.ALLOW_ENV, raising=False)
    monkeypatch.setenv("PLATFORM_MCP_MAX_DOWNLOAD_MB", "0.001")  # 1000 bytes
    respx.get("https://93.184.215.14/big.png", headers={"host": "cdn.example"}).mock(return_value=httpx.Response(200, content=b"x" * 5000))
    gen = respx.post("https://mp.example/v2/generate").mock(return_value=httpx.Response(200, json={"id": "j1", "status": "queued"}))
    res = await _mp_server().call_tool("generate_image", {"prompt": "x", "image_url": "https://cdn.example/big.png"})
    assert res.is_error and "larger" in res.structured_content["message"] and not gen.called


# ---------------------------------------------------------------- SR-03: tool arguments spliced raw into the URL path

PATH_SPEC = {"id": "pathy", "category": "jobs", "label": "Pathy", "docs_url": "https://docs.example/", "verified_at": "2026-10-01",
             "adapter": {"base_url": "https://api.pathy.example/v1", "rate_per_second": 50, "auth": {"type": "header", "header": "X-Api-Key", "field": "api_key", "fields": [{"name": "api_key"}]},
                         "tools": {"get_posting": {"path": "/jobs/{id}", "result": {"fields": {"id": "id", "title": "title"}}},
                                   "search": {"path": "/boards/{board}/jobs", "path_params": {"board": "fmt:{@org}/{query}"}, "params": {"page": "page"},
                                              "result": {"items": "jobs", "key": "postings", "fields": {"id": "id"}}}},
                         "config_fields": [{"name": "org"}]}}


def _path_server():
    t = Transport(PATH_SPEC["adapter"]["base_url"], PATH_SPEC["adapter"]["auth"], {"api_key": "KEY-pathy-1", "org": "acme"}, 50, "test")
    return build_server(PATH_SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_path_arguments_cannot_change_the_endpoint():
    route = respx.get(url__startswith="https://api.pathy.example/").mock(return_value=httpx.Response(200, json={"id": "1", "title": "t", "jobs": []}))
    s = _path_server()
    for raw, want in (("7?delete=true#x", "/v1/jobs/7%3Fdelete=true%23x"), ("a b", "/v1/jobs/a%20b"), ("100%", "/v1/jobs/100%25"),
                      ("urn%3Ali%3Ashare%3A1", "/v1/jobs/urn%3Ali%3Ashare%3A1"), ("gb/00102498", "/v1/jobs/gb/00102498"),
                      ("abc-1_2.3~:@!$&'()*+,;=", "/v1/jobs/abc-1_2.3~:@!$&'()*+,;="), ("caf\u00e9", "/v1/jobs/caf%C3%A9")):
        res = await s.call_tool("get_posting", {"id": raw})
        assert res.is_error is False, (raw, res.structured_content)
        req = route.calls.last.request
        assert req.url.raw_path.decode().split("?")[0] == want, raw
        assert req.url.host == "api.pathy.example" and not req.url.query
    n = len(route.calls)
    for raw in ("..", ".", "../../admin/users", "x/../../admin", "%2e%2E/admin", "a/.%2e/b"):
        res = await s.call_tool("get_posting", {"id": raw})
        assert res.is_error and res.structured_content["error"] == "invalid_input", raw
    # a catalog path_params template keeps its own slashes; dot segments from an argument are refused there too
    res = await s.call_tool("search", {"query": "eng/../../x"})
    assert res.is_error and res.structured_content["error"] == "invalid_input"
    assert len(route.calls) == n
    await s.call_tool("search", {"query": "eng"})
    assert route.calls.last.request.url.raw_path.decode().split("?")[0] == "/v1/boards/acme/eng/jobs"


# ---------------------------------------------------------------- SR-05: 401 re-login must rebuild the request with the new token

def _oauth_spec(auth_extra: dict, path: str):
    auth = {"type": "oauth2_client_credentials", "token_url": "https://auth.tok.example/token", "fields": [{"name": "client_id"}, {"name": "client_secret"}], **auth_extra}
    return {"id": "tok", "category": "jobs", "label": "Tok", "docs_url": "https://docs.example/", "verified_at": "2026-10-01",
            "adapter": {"base_url": "https://api.tok.example", "rate_per_second": 50, "auth": auth,
                        "tools": {"get_posting": {"path": path, "result": {"fields": {"id": "id", "title": "title"}}}}}}


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("auth_extra,path,where", [
    ({"token_param": "access_token"}, "/jobs/{id}", "query"),
    ({"header": ""}, "/t/{access_token}/jobs/{id}", "path"),
    ({}, "/jobs/{id}", "header"),
])
async def test_401_retry_carries_the_new_token(auth_extra, path, where):
    spec = _oauth_spec(auth_extra, path)
    minted = iter(["OLD-token-1", "NEW-token-2"])
    respx.post("https://auth.tok.example/token").mock(side_effect=lambda req: httpx.Response(200, json={"access_token": next(minted), "expires_in": 3600}))
    calls = []

    def api(req):
        calls.append(req)
        return httpx.Response(401, json={"error": "expired"}) if len(calls) == 1 else httpx.Response(200, json={"id": "9", "title": "t"})
    respx.get(url__startswith="https://api.tok.example/").mock(side_effect=api)
    t = Transport(spec["adapter"]["base_url"], spec["adapter"]["auth"], {"client_id": "cid", "client_secret": "csecret"}, 50, "test")
    res = await build_server(spec, transport=t).call_tool("get_posting", {"id": "9"})
    assert res.is_error is False, res.structured_content
    retry = calls[1]
    seen = {"query": retry.url.params.get("access_token"), "path": retry.url.path, "header": retry.headers.get("authorization")}[where]
    assert "NEW-token-2" in seen and "OLD-token-1" not in str(retry.url) + str(retry.headers.get("authorization"))


# ---------------------------------------------------------------- SR-09: redaction of encoded secrets and auth schemes

@pytest.mark.asyncio
@respx.mock
async def test_basic_auth_and_url_encoded_secrets_are_redacted():
    auth = {"type": "basic", "username_field": "user", "password_field": "password", "fields": [{"name": "user"}, {"name": "password"}]}
    spec = {"id": "basicx", "category": "jobs", "label": "B", "docs_url": "https://docs.example/", "verified_at": "2026-10-01",
            "adapter": {"base_url": "https://api.basic.example", "rate_per_second": 50, "auth": auth,
                        "tools": {"get_posting": {"path": "/jobs/{id}", "result": {"fields": {"id": "id"}}}}}}
    b64 = base64.b64encode(b"svc-user:p@ss w0rd/+").decode()
    echo = f"bad request; you sent Authorization: Basic {b64} and password=p%40ss%20w0rd%2F%2B (form: p%40ss+w0rd%2F%2B)"
    respx.get("https://api.basic.example/jobs/1").mock(return_value=httpx.Response(500, text=echo))
    t = Transport("https://api.basic.example", auth, {"user": "svc-user", "password": "p@ss w0rd/+"}, 50, "test")
    res = await build_server(spec, transport=t).call_tool("get_posting", {"id": "1"})
    msg = res.structured_content["message"]
    assert res.is_error and b64 not in msg and "p%40ss" not in msg and "w0rd" not in msg, msg
    assert credentials.scrub("Authorization: Bearer abcdefghijkl123") == "Authorization: Bearer <redacted>"
    assert credentials.scrub('{"authorization": "Basic Zm9vOmJhcg=="}') == '{"authorization": <redacted>}'


# ---------------------------------------------------------------- SR-10: rotated refresh-token state file

@pytest.mark.asyncio
@respx.mock
async def test_state_file_is_private_and_never_follows_a_planted_symlink(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(state))
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    state.mkdir(mode=0o755)
    (state / "rot.tmp").symlink_to(victim)          # the old Python temp name
    (state / "rot.json.tmp").symlink_to(victim)     # the old TypeScript temp name
    (state / "rot.json").write_text(json.dumps({"refresh_token": "R-old-123456"}))
    os.chmod(state / "rot.json", 0o644)
    auth = {"type": "oauth2_refresh_token", "token_url": "https://auth.rot.example/token", "state_key": "rot",
            "fields": [{"name": "client_id"}, {"name": "refresh_token"}]}
    respx.post("https://auth.rot.example/token").mock(return_value=httpx.Response(200, json={"access_token": "A-123456", "refresh_token": "R-new-654321", "expires_in": 3600}))
    respx.get("https://api.rot.example/jobs/1").mock(return_value=httpx.Response(200, json={"id": "1"}))
    spec = {"id": "rot", "category": "jobs", "label": "R", "docs_url": "https://docs.example/", "verified_at": "2026-10-01",
            "adapter": {"base_url": "https://api.rot.example", "rate_per_second": 50, "auth": auth, "tools": {"get_posting": {"path": "/jobs/{id}", "result": {"fields": {"id": "id"}}}}}}
    t = Transport("https://api.rot.example", auth, {"client_id": "c", "refresh_token": "R-env-000000"}, 50, "test")
    assert (await build_server(spec, transport=t).call_tool("get_posting", {"id": "1"})).is_error is False
    assert victim.read_text() == "keep"
    assert json.loads((state / "rot.json").read_text()) == {"refresh_token": "R-new-654321"}
    assert stat.S_IMODE((state / "rot.json").stat().st_mode) == 0o600
    fresh = tmp_path / "fresh" / "nested"
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(fresh))
    t2 = Transport("https://api.rot.example", auth, {"client_id": "c", "refresh_token": "R-env-000000"}, 50, "test")
    t2._store_rotated_refresh_token("R-third-999999")
    assert stat.S_IMODE(fresh.stat().st_mode) == 0o700 and stat.S_IMODE((fresh / "rot.json").stat().st_mode) == 0o600


# ---------------------------------------------------------------- SR-11: a cursor that does not advance ends the walk

@pytest.mark.asyncio
@respx.mock
async def test_repeated_cursor_is_not_offered_again():
    spec = {"id": "cur", "category": "jobs", "label": "C", "docs_url": "https://docs.example/", "verified_at": "2026-10-01",
            "adapter": {"base_url": "https://api.cur.example", "rate_per_second": 50, "auth": {"type": "none"},
                        "tools": {"search": {"path": "/jobs", "params": {"after": "cursor", "n": "limit"}, "result": {"items": "jobs", "key": "postings", "next_cursor": "next", "fields": {"id": "id"}}}}}}
    respx.get(url__startswith="https://api.cur.example/jobs").mock(return_value=httpx.Response(200, json={"jobs": [{"id": 1}], "next": "C2"}))
    s = build_server(spec, transport=Transport("https://api.cur.example", {"type": "none"}, {}, 50, "test"))
    first = (await s.call_tool("search", {"query": "x", "limit": 1})).structured_content
    assert first["next_cursor"] == "C2"
    again = (await s.call_tool("search", {"query": "x", "limit": 1, "cursor": "C2"})).structured_content
    assert again["next_cursor"] is None and again["next_page"] is None


# ---------------------------------------------------------------- SR-16: the rate limit holds under concurrent calls

@pytest.mark.asyncio
@respx.mock
async def test_concurrent_requests_respect_rate_per_second():
    import asyncio
    import time as _time
    times = []

    def hit(req):
        times.append(_time.monotonic())
        return httpx.Response(200, json={"id": "1"})
    respx.get(url__startswith="https://api.rl.example/").mock(side_effect=hit)
    spec = {"id": "rl", "category": "jobs", "label": "R", "docs_url": "https://docs.example/", "verified_at": "2026-10-01",
            "adapter": {"base_url": "https://api.rl.example", "rate_per_second": 10, "auth": {"type": "none"}, "tools": {"get_posting": {"path": "/jobs/{id}", "result": {"fields": {"id": "id"}}}}}}
    s = build_server(spec, transport=Transport("https://api.rl.example", {"type": "none"}, {}, 10, "test"))
    t0 = _time.monotonic()
    await asyncio.gather(*(s.call_tool("get_posting", {"id": str(i)}) for i in range(20)))
    assert max(times) - t0 >= 0.85  # a burst of 10, then one every 100 ms
