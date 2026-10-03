"""Vendor environments (adapter.environments, PLATFORM_MCP_<ID>_ENV, PLATFORM_MCP_<ID>_BASE_URL) in the Python
runtime: environment selection, override validation, OAuth2 token URL switching, per-environment refresh-token
state and redaction. The TypeScript twin is environments.typescript.test.mjs; both read
tests/fixtures/environments_cases.json and assert the same outputs."""
import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
sys.path.insert(0, str(ROOT / "tools"))
from platform_mcp_hub import environment  # noqa: E402
from platform_mcp_hub.credentials import scrub  # noqa: E402
from platform_mcp_hub.errors import InvalidInput  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

CASES = json.loads((ROOT / "tests" / "fixtures" / "environments_cases.json").read_text(encoding="utf-8"))
CREDS = {"CLIENT_ID": "cid-0123456789", "CLIENT_SECRET": "csecret-0123456789", "REFRESH_TOKEN": "rt-0123456789abcdef"}


@pytest.fixture(autouse=True)
def _isolated_secrets():
    """Overrides registered as secrets here must not redact URLs in other test modules of the session."""
    from platform_mcp_hub import credentials
    saved = set(credentials._KNOWN)
    yield
    credentials._KNOWN.clear()
    credentials._KNOWN.update(saved)


def spec(adapter: dict | None = None) -> dict:
    return {"id": "shop", "category": "ecommerce_channels", "docs_url": "https://docs.shop.example", "adapter": json.loads(json.dumps(adapter or CASES["adapter"]))}


def env_of(case_env: dict) -> dict:
    return {f"PLATFORM_MCP_SHOP_{k}": v for k, v in case_env.items()}


@pytest.mark.parametrize("case", CASES["select"], ids=lambda c: json.dumps(c["env"]))
def test_select_environment(case):
    adapter = spec()["adapter"]
    if "error" in case:
        with pytest.raises(InvalidInput) as exc:
            environment.select("shop", adapter, env_of(case["env"]))
        assert str(exc.value) == case["error"]
        return
    eff, name = environment.select("shop", adapter, env_of(case["env"]))
    assert name == case["environment"]
    assert eff["base_url"] == case["base_url"]
    assert eff["auth"]["token_url"] == case["token_url"]
    assert eff["auth"]["scope"] == case["scope"]
    assert eff["tools"]["me"]["path"] == case["me_path"]
    assert eff["tools"]["list_orders"]["path"] == "/orders"
    assert eff.get("headers") == case["headers"]
    assert eff["auth"].get("auth_url") == case.get("auth_url", eff["auth"].get("auth_url"))
    assert "environments" not in eff
    assert adapter == spec()["adapter"], "the catalog spec is never mutated"


@pytest.mark.parametrize("value,valid,why", CASES["overrides"], ids=[c[0] for c in CASES["overrides"]])
def test_base_url_override_validation(value, valid, why):
    assert environment.valid_https_url(value) is valid
    env = {"PLATFORM_MCP_SHOP_BASE_URL": value}
    if valid:
        eff, name = environment.select("shop", spec()["adapter"], env)
        assert eff["base_url"] == value and name == "production+base_url"
        return
    with pytest.raises(InvalidInput) as exc:
        environment.select("shop", spec()["adapter"], env)
    msg = str(exc.value)
    assert msg == f"configuration: PLATFORM_MCP_SHOP_BASE_URL is not a valid override: {why}"
    assert value == "https://" or value not in msg
    assert "hunter2secret" not in msg and "abcdef123456" not in msg


def test_state_key_is_per_environment():
    assert environment.state_key("shop", "production") == "shop"
    assert environment.state_key("shop", "production+base_url") == "shop"
    assert environment.state_key("shop", "sandbox") == "shop.sandbox"
    assert environment.state_key("shop", "sandbox+base_url") == "shop.sandbox"


def _mock_shop(router, token_host: str, api_base: str, reports_host: str):
    token = router.post(f"https://{token_host}/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": f"at-{token_host}", "expires_in": 3600}))
    orders = router.get(f"{api_base}/orders").mock(return_value=httpx.Response(200, json={"orders": [{"id": "o-1"}]}))
    me = router.get(f"https://{reports_host}/me").mock(return_value=httpx.Response(200, json={"id": "me-1", "name": "Shop"}))
    return token, orders, me


@pytest.mark.asyncio
@pytest.mark.parametrize("env,token_host,api_base,reports_host,scope", [
    ({}, "auth.shop.example", "https://api.shop.example/v1", "reports.shop.example", "prod.scope"),
    ({"ENV": "sandbox"}, "api.sandbox.shop.example", "https://api.sandbox.shop.example/v1", "reports.sandbox.shop.example", "sandbox.scope"),
    ({"ENV": "dynamic"}, "auth.sandbox.shop.example", "https://api.sandbox.shop.example/v1", "reports.shop.example", "prod.scope"),
])
async def test_oauth2_token_url_and_hosts_switch_with_the_environment(monkeypatch, env, token_host, api_base, reports_host, scope):
    for k, v in {**CREDS, **env}.items():
        monkeypatch.setenv(f"PLATFORM_MCP_SHOP_{k}", v)
    with respx.mock(assert_all_mocked=True) as router:
        token, orders, me = _mock_shop(router, token_host, api_base, reports_host)
        s = build_server(spec())
        r = await s.call_tool("list_orders", {})
        assert not r.is_error, r.structured_content
        assert r.structured_content["orders"][0]["id"] == "o-1"
        r2 = await s.call_tool("me", {})
        assert not r2.is_error, r2.structured_content
        assert token.call_count == 1
        form = dict(x.split("=", 1) for x in token.calls[0].request.content.decode().split("&"))
        assert form["grant_type"] == "refresh_token" and form["scope"] == scope
        api_req = orders.calls[0].request
        assert api_req.headers["authorization"] == f"Bearer at-{token_host}"
        assert api_req.headers["x-api-version"] == "3"
        assert api_req.headers.get("x-sandbox") == ("v2" if env.get("ENV") == "dynamic" else None)
        assert me.call_count == 1


@pytest.mark.asyncio
async def test_bad_environment_is_a_clean_tool_error(monkeypatch):
    for k, v in {**CREDS, "ENV": "staging"}.items():
        monkeypatch.setenv(f"PLATFORM_MCP_SHOP_{k}", v)
    with respx.mock(assert_all_called=False) as router:
        route = router.route().mock(return_value=httpx.Response(200, json={}))
        r = await build_server(spec()).call_tool("list_orders", {})
        assert r.is_error
        assert r.structured_content == {"error": "invalid_input", "message": CASES["select"][-2]["error"]}
        assert route.call_count == 0, "nothing is sent when the environment is unknown"


@pytest.mark.asyncio
async def test_invalid_override_is_a_tool_error_that_never_echoes_the_value(monkeypatch):
    secret_url = "https://svc-user:p4ssw0rd-9f8e7d@gateway.corp.example/api"
    for k, v in {**CREDS, "BASE_URL": secret_url}.items():
        monkeypatch.setenv(f"PLATFORM_MCP_SHOP_{k}", v)
    r = await build_server(spec()).call_tool("list_orders", {})
    assert r.is_error and r.structured_content["error"] == "invalid_input"
    text = json.dumps(r.structured_content)
    assert "p4ssw0rd" not in text and "gateway.corp.example" not in text and "svc-user" not in text
    assert "PLATFORM_MCP_SHOP_BASE_URL" in text


@pytest.mark.asyncio
async def test_override_host_is_redacted_from_upstream_and_network_errors(monkeypatch):
    private = "https://gw-7f3a.internal.corp.example/shop-proxy"
    for k, v in {**CREDS, "BASE_URL": private, "ENV": "sandbox"}.items():
        monkeypatch.setenv(f"PLATFORM_MCP_SHOP_{k}", v)
    with respx.mock(assert_all_mocked=True) as router:
        router.post("https://api.sandbox.shop.example/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "at-sandbox-777777", "expires_in": 3600}))
        router.get(f"{private}/orders").mock(return_value=httpx.Response(502, text=f"upstream {private}/orders failed; token at-sandbox-777777"))
        s = build_server(spec())
        r = await s.call_tool("list_orders", {})
        assert r.is_error and r.structured_content["error"] == "upstream_error"
        msg = r.structured_content["message"]
        assert private not in msg and "at-sandbox-777777" not in msg and "<redacted>" in msg
    with respx.mock(assert_all_mocked=True) as router:
        router.get(f"{private}/orders").mock(side_effect=httpx.ConnectError(f"cannot connect to {private}/orders"))
        r = await s.call_tool("list_orders", {})
        assert r.is_error
        assert private not in json.dumps(r.structured_content)
    assert private not in scrub(f"GET {private}/orders")


@pytest.mark.asyncio
async def test_rotated_refresh_tokens_are_saved_per_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    for k, v in {**CREDS, "ENV": "sandbox"}.items():
        monkeypatch.setenv(f"PLATFORM_MCP_SHOP_{k}", v)
    with respx.mock(assert_all_mocked=True) as router:
        router.post("https://api.sandbox.shop.example/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "at-sb-000000", "refresh_token": "rt-rotated-sandbox-1", "expires_in": 3600}))
        router.get("https://api.sandbox.shop.example/v1/orders").mock(return_value=httpx.Response(200, json={"orders": []}))
        r = await build_server(spec()).call_tool("list_orders", {})
        assert not r.is_error, r.structured_content
    assert (tmp_path / "shop.sandbox.json").exists()
    assert not (tmp_path / "shop.json").exists(), "a sandbox token never replaces the production one"


def test_lint_rules():
    base = spec()["adapter"]
    assert environment.lint(base) == []
    bad = json.loads(json.dumps(base))
    bad["environments"] = {
        "production": {"same_host": True, "docs": "https://x.example", "verified_at": "2026-09-27", "notes": "n"},
        "a": {"base_url": "http://api.sandbox.shop.example", "docs": "https://x.example", "verified_at": "2026-09-27", "notes": "n"},
        "b": {"same_host": True, "base_url": "https://api.sandbox.shop.example", "docs": "https://x.example", "verified_at": "2026-09-27", "notes": "n"},
        "c": {"hosts": {"unknown.example": "x.example"}, "docs": "https://x.example", "verified_at": "2026-09-27", "notes": "n"},
        "d": {"base_url": "https://api.sandbox.shop.example"},
        "e": {"docs": "https://x.example", "verified_at": "2026-09-27", "notes": "n"},
        "f": {"base_url": "https://api.sandbox.shop.example/v1?x=1", "sandbox_key": "zzz", "docs": "https://x.example", "verified_at": "2026-09-27", "notes": "n"},
    }
    bad["config_fields"] = [{"name": "env"}]
    errs = "\n".join(environment.lint(bad))
    for needle in ["environments.production: the name", "environments.a.base_url must be an https URL", "environments.b: same_host cannot be combined",
                   "environments.c.hosts: 'unknown.example' is not a host", "environments.d.docs must cite", "environments.d.verified_at",
                   "environments.d.notes", "environments.e: set base_url", "environments.f: unknown keys ['sandbox_key']",
                   "environments.f.base_url must be an https URL", "field named 'env' collides"]:
        assert needle in errs, needle


def test_lint_catalog_accepts_every_declared_environment_and_rejects_bad_checks(tmp_path):
    from platform_mcp_hub import lint as lint_catalog
    served = [p for p in (ROOT / "catalog").glob("*/*.json") if p.parent.name not in ("schema", "sources") and "environments" in json.loads(p.read_text(encoding="utf-8")).get("adapter", {})]
    assert len(served) >= 15
    for p in served:
        errors, _ = lint_catalog.lint(p)
        assert errors == [], (p, errors)
        for name, env in json.loads(p.read_text(encoding="utf-8"))["adapter"]["environments"].items():
            assert env["docs"].startswith("https://") and env["notes"], (p, name)
    entry = json.loads((ROOT / "catalog" / "ecommerce_channels" / "ebay.json").read_text(encoding="utf-8"))
    entry["environment_checks"] = {"sandbox": {"live_check": {"date": "2026-09-27", "status": "working", "egress": "dev", "notes": "ok"}},
                                   "staging": {"live_check": {"date": "bad", "status": "nope", "egress": "", "notes": 1}}}
    d = tmp_path / "ecommerce_channels"
    d.mkdir()
    (d / "ebay.json").write_text(json.dumps(entry), encoding="utf-8")
    errors, _ = lint_catalog.lint(d / "ebay.json")
    text = "\n".join(errors)
    assert "environment_checks.staging: 'staging' is not declared" in text
    assert "environment_checks.staging.live_check.date must be YYYY-MM-DD" in text
    assert "environment_checks.sandbox" not in text


def test_generated_manifests_advertise_the_environment_variables():
    sj = json.loads((ROOT / "servers" / "ecommerce_channels" / "ebay" / "server.json").read_text(encoding="utf-8"))
    for pkg in sj["packages"]:
        env = {v["name"]: v for v in pkg["environmentVariables"]}
        assert env["PLATFORM_MCP_EBAY_ENV"]["choices"] == ["production", "sandbox"]
        assert env["PLATFORM_MCP_EBAY_ENV"]["default"] == "production" and env["PLATFORM_MCP_EBAY_ENV"]["isRequired"] is False
        assert "sandbox = https://api.sandbox.ebay.com" in env["PLATFORM_MCP_EBAY_ENV"]["description"]
        assert env["PLATFORM_MCP_EBAY_BASE_URL"]["isSecret"] is False
    from platform_mcp_hub import catalog
    ebay = json.loads((ROOT / "catalog" / "ecommerce_channels" / "ebay.json").read_text(encoding="utf-8"))
    assert sj["packages"][0]["environmentVariables"] == catalog.env_vars(ebay), "server.json advertises what `describe` lists"
    assert [a["value"] for a in sj["packages"][0]["packageArguments"]] == ["serve", "ebay"]
    manifest = json.loads((ROOT / "servers" / "ecommerce_channels" / "ebay" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["user_config"]["platform_mcp_ebay_env"]["default"] == "production"
    assert manifest["server"]["mcp_config"]["env"]["PLATFORM_MCP_EBAY_ENV"] == "${user_config.platform_mcp_ebay_env}"
    walmart = json.loads((ROOT / "servers" / "ecommerce_channels" / "walmart" / "server.json").read_text(encoding="utf-8"))
    choices = {v["name"]: v.get("choices") for v in walmart["packages"][0]["environmentVariables"]}
    assert choices["PLATFORM_MCP_WALMART_ENV"] == ["production", "sandbox", "sandbox_dynamic"]
    plain = json.loads((ROOT / "servers" / "jobs" / "reed" / "server.json").read_text(encoding="utf-8"))
    assert not any(v["name"].endswith("_ENV") for p in plain["packages"] for v in p["environmentVariables"])
