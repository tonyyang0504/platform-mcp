"""Signing test vectors published by the vendors (and the fixes found by the credential-free auth
audit, docs/AUTH_AUDIT.md). Every expected value below is copied from the cited page; none is
computed by this repository.

- AWS SigV4: the AWS signature test suite (awslabs/aws-c-auth tests/aws-signing-test-suite/v4),
  credentials AKIDEXAMPLE / wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY, 20150830T123600Z, us-east-1/service.
- OAuth 1.0a: OAuth Core 1.0 Appendix A.5 (photos.example.net) and X's "Creating a signature" page
  (https://docs.x.com/resources/fundamentals/authentication/oauth-1-0a/creating-a-signature), which
  signs a form-encoded body parameter (RFC 5849 3.4.1.3.1).
- HMAC: Binance "SIGNED endpoint examples" (binance/binance-spot-api-docs rest-api.md, ASCII and
  non-ASCII symbol) and Kaufland Seller API "Signing requests" (https://sellerapi.kaufland.com/?page=rest-api).
- JWT HS256: the default example token published on https://jwt.io (header {"alg":"HS256","typ":"JWT"}).
"""
import base64
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
sys.path.insert(0, str(ROOT / "tools"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

def _entry(rel: str) -> dict:
    return json.loads((ROOT / "catalog" / rel).read_text(encoding="utf-8"))


def _server(auth, tools, creds, base, category="ecommerce_channels", headers=None):
    spec = {"id": "vec", "category": category, "label": "Vec", "docs_url": "https://docs.example/", "verified_at": "2026-09-26",
            "adapter": {"base_url": base, "rate_per_second": 50, "auth": auth, "tools": tools, "headers": headers or {}}}
    return build_server(spec, transport=Transport(base, auth, creds, 50, "test"))


# ---- AWS SigV4 test suite ---------------------------------------------------------------------------

AWS_VECTORS = [  # (suite case, method, path, query pairs in request order, expected signature)
    ("get-vanilla", "GET", "/", [], "5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31"),
    ("get-vanilla-query-order-key-case", "GET", "/", [("Param2", "value2"), ("Param1", "value1")], "b97d918cfa904a5beff61c982a1b6f458b799221646efd99d3219ec94cdf2500"),
    ("get-vanilla-query-unreserved", "GET", "/", [("-._~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "-._~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")], "9c3e54bfcdf0b19771a7f523ee5669cdf59bc7cc0884027167c21bb143a40197"),
    ("get-vanilla-empty-query-key", "GET", "/", [("Param1", "value1")], "a67d582fa61cc504c4bae71f336f98b97f1ea3c7a6bfe1b6e45aec72011b9aeb"),
    ("get-utf8", "GET", "/ሴ", [], "8318018e0b0f223aa2bbf98705b62bb787dc9c0e678f255a891fd03141be5d85"),
    ("get-space-normalized", "GET", "/example space/", [], "652487583200325589f1fba4c7e578f72c47cb61beeca81406b39ddec1366741"),
    ("post-vanilla", "POST", "/", [], "5da7c1a2acd57cee7505fc6676e4e544621c30862966e37dddb68e92efbe5d6b"),
    ("post-vanilla-query", "POST", "/", [("Param1", "value1")], "28038455d6de14eafc1f9222cf5aa6f1a96197d7deb8263271d420d138af7f11"),
]


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("case,method,path,query,signature", AWS_VECTORS, ids=[v[0] for v in AWS_VECTORS])
async def test_aws_sigv4_test_suite(monkeypatch, case, method, path, query, signature):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1440938160.0)  # 20150830T123600Z
    route = respx.route(url__startswith="https://example.amazonaws.com/").mock(return_value=httpx.Response(200, json={}))
    auth = {"type": "none", "fields": [{"name": "access_key_id"}, {"name": "secret_access_key"}], "sign": {"mode": "aws_sigv4", "service": "service", "region": "us-east-1"}}
    tools = {"me": {"kind": "probe", "method": method, "path": path, "fixed_params": dict(query)}}
    server = _server(auth, tools, {"access_key_id": "AKIDEXAMPLE", "secret_access_key": "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"}, "https://example.amazonaws.com")
    assert (await server.call_tool("me", {})).is_error is False
    h = route.calls[0].request.headers
    assert h["X-Amz-Date"] == "20150830T123600Z"
    assert h["Authorization"] == f"AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20150830/us-east-1/service/aws4_request, SignedHeaders=host;x-amz-date, Signature={signature}"


# ---- OAuth 1.0a ---------------------------------------------------------------------------------------

def _oauth_header(req) -> dict:
    from urllib.parse import unquote
    hdr = req.headers["Authorization"]
    assert hdr.startswith("OAuth ")
    return {k: unquote(v.strip('"')) for k, v in (x.split("=", 1) for x in hdr[6:].split(", "))}


@pytest.mark.asyncio
@respx.mock
async def test_oauth1_core_appendix_a5(monkeypatch):
    import time as _t
    import uuid as _uuid
    monkeypatch.setattr(_t, "time", lambda: 1191242096.0)
    monkeypatch.setattr(_uuid, "uuid4", lambda: SimpleNamespace(hex="kllo9940pd9333jh"))
    route = respx.get(url__startswith="http://photos.example.net/photos").mock(return_value=httpx.Response(200, json={}))
    auth = {"type": "none", "fields": [], "sign": {"mode": "oauth1"}}
    tools = {"me": {"kind": "probe", "path": "/photos", "fixed_params": {"file": "vacation.jpg", "size": "original"}}}
    creds = {"consumer_key": "dpf43f3p2l4k3l03", "consumer_secret": "kd94hf93k423kf44", "access_token": "nnch734d00sl2jdk", "access_token_secret": "pfkkdhi9sl3r4s00"}
    assert (await _server(auth, tools, creds, "http://photos.example.net").call_tool("me", {})).is_error is False
    o = _oauth_header(route.calls[0].request)
    assert o["oauth_nonce"] == "kllo9940pd9333jh" and o["oauth_timestamp"] == "1191242096"
    assert o["oauth_signature"] == "tR3+Ty81lMeYAr/Fid0kMTYa/WM="


@pytest.mark.asyncio
@respx.mock
async def test_oauth1_signs_form_body_parameters_x_docs_example(monkeypatch):
    """RFC 5849 3.4.1.3.1: a form-encoded body is part of the signature base string (X's worked example)."""
    import time as _t
    import uuid as _uuid
    monkeypatch.setattr(_t, "time", lambda: 1318622958.0)
    monkeypatch.setattr(_uuid, "uuid4", lambda: SimpleNamespace(hex="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg"))
    route = respx.post(url__startswith="https://api.x.com/1.1/statuses/update.json").mock(return_value=httpx.Response(200, json={"id_str": "1"}))
    auth = {"type": "none", "fields": [], "sign": {"mode": "oauth1"}}
    tools = {"publish_text": {"method": "POST", "path": "/1.1/statuses/update.json", "fixed_params": {"include_entities": "true"},
                              "body_format": "form", "body": {"status": "text"}, "result": {"fields": {"id": "id_str"}}}}
    creds = {"consumer_key": "xvz1evFS4wEEPTGEFPHBog", "consumer_secret": "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
             "access_token": "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb", "access_token_secret": "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE"}
    res = await _server(auth, tools, creds, "https://api.x.com", category="social").call_tool("publish_text", {"text": "Hello Ladies + Gentlemen, a signed OAuth request!"})
    assert res.is_error is False
    req = route.calls[0].request
    assert _oauth_header(req)["oauth_signature"] == "Ls93hJiZbQ3akF3HF3x1Bz8/zU4="
    assert b"status=Hello" in req.content


# ---- HMAC request signing (vendor examples, through the catalog's own auth blocks) -------------------

@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("symbol,signature", [
    ("LTCBTC", "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"),
    ("１２３４５６", "e1353ec6b14d888f1164ae9af8228a3dbd508bc82eb867db8ab6046442f33ef3"),
])
async def test_binance_documented_signature_examples(monkeypatch, symbol, signature):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1499827319.5591)  # timestamp=1499827319559
    e = _entry("trading/binance_spot.json")
    auth = e["adapter"]["auth"]
    tool = {**e["adapter"]["tools"]["place_order"], "fixed_params": {"recvWindow": "5000"}}
    route = respx.post(url__startswith="https://api.binance.com/api/v3/order").mock(return_value=httpx.Response(200, json={"orderId": 1}))
    server = _server(auth, {"place_order": tool}, {"api_key": "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A",
                                                  "api_secret": "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"},
                     "https://api.binance.com", category="trading")
    res = await server.call_tool("place_order", {"symbol": symbol, "side": "buy", "type": "limit", "quantity": 1, "price": 0.1})
    assert res.is_error is False
    query = str(route.calls[0].request.url).split("?", 1)[1]
    assert query.split("&signature=")[0].endswith("&price=0.1&recvWindow=5000&timestamp=1499827319559")
    assert query.split("&signature=")[1] == signature


@pytest.mark.asyncio
@respx.mock
async def test_kaufland_documented_signature_example(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1411055926.0)
    e = _entry("ecommerce_channels/kaufland.json")
    auth = e["adapter"]["auth"]
    route = respx.post("https://sellerapi.kaufland.com/v2/units/").mock(return_value=httpx.Response(200, json={}))
    tools = {"me": {"kind": "probe", "method": "POST", "path": "/v2/units/"}}
    creds = {f["name"]: "x" * 32 for f in auth["fields"]}
    creds["secret_key"] = "a7d0cb1da1ddbc86c96ee5fedd341b7d8ebfbb2f5c83cfe0909f4e57f05dd403"
    server = _server(auth, tools, creds, "https://sellerapi.kaufland.com", headers=e["adapter"].get("headers"))
    assert (await server.call_tool("me", {})).is_error is False
    h = route.calls[0].request.headers
    assert h["Shop-Timestamp"] == "1411055926"
    assert h["Shop-Signature"] == "da0b65f51c0716c1d3fa658b7eaf710583630a762a98c9af8e9b392bd9df2e2a"


# ---- JWT HS256 ------------------------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_jwt_hs256_published_example(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1516239022.0)
    route = respx.get("https://api.vec.example/me").mock(return_value=httpx.Response(200, json={}))
    auth = {"type": "none", "fields": [], "sign": {"mode": "jwt_hs256", "key_field": "api_secret",
            "claims": {"sub": "1234567890", "name": "John Doe", "iat": "{timestamp_s}"}, "headers": {"Authorization": "Bearer {signature}"}}}
    server = _server(auth, {"me": {"kind": "probe", "path": "/me"}}, {"api_secret": "your-256-bit-secret"}, "https://api.vec.example")
    assert (await server.call_tool("me", {})).is_error is False
    assert route.calls[0].request.headers["Authorization"] == ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                                                               "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
                                                               "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")


# ---- catalog fixes found by the audit -------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("since,sent", [("2026-09-01", "2026-09-01T00:00:00.000Z"), ("2026-09-01T10:30:00+02:00", "2026-09-01T08:30:00.000Z")])
async def test_wix_orders_filter_sends_an_iso_datetime(since, sent):
    """Wix answered 400 '2026-09-01 is not a valid dateTime filter value' for a bare date (audit 2026-09-26)."""
    e = _entry("ecommerce_channels/wix_stores.json")
    a = e["adapter"]
    route = respx.post("https://www.wixapis.com/ecom/v1/orders/search").mock(return_value=httpx.Response(200, json={"orders": []}))
    server = build_server(e, transport=Transport(a["base_url"], a["auth"], {"api_key": "k" * 12, "site_id": "s" * 12}, 50, "test"))
    assert (await server.call_tool("list_orders", {"since": since})).is_error is False
    assert json.loads(route.calls[0].request.content)["search"]["filter"]["createdDate"]["$gte"] == sent


# ---- lint: the auth_audit block --------------------------------------------------------------------------

def test_lint_accepts_and_rejects_auth_audit_blocks():
    from platform_mcp_hub.lint import lint_auth_audit
    served = {"adapter": {"auth": {"type": "bearer"}, "tools": {}}}
    good = {"date": "2026-09-26", "status": "spec_conformant", "evidence": ["probe: 3/3 tools answered 401"], "notes": "-"}
    assert lint_auth_audit({**served, "auth_audit": good}) == []
    assert lint_auth_audit(served) == []
    assert lint_auth_audit({**served, "auth_audit": {**good, "status": "fine"}})
    assert lint_auth_audit({**served, "auth_audit": {**good, "evidence": []}})
    assert lint_auth_audit({**served, "auth_audit": {**good, "extra": 1}})
    assert lint_auth_audit({**served, "auth_audit": {**good, "date": "26/09/2026"}})
    assert lint_auth_audit({"adapter": {"auth": {"type": "none"}, "tools": {}}, "auth_audit": good})
    assert lint_auth_audit({"auth_audit": good})


def test_every_in_scope_entry_carries_an_auth_audit_block():
    import glob
    missing = []
    for f in glob.glob(str(ROOT / "catalog" / "*" / "*.json")):
        if "/schema/" in f or "/sources/" in f or f.endswith("index.json"):
            continue
        e = json.loads(Path(f).read_text(encoding="utf-8"))
        if e.get("adapter") and e["adapter"].get("auth", {}).get("type", "none") != "none" and "auth_audit" not in e:
            missing.append(e["id"])
    assert not missing, missing


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("rel,verb,args,url,body", [
    ("ads/tiktok.json", "list_accounts", {}, "https://business-api.tiktok.com/open_api/v1.3/oauth2/advertiser/get/",
     {"code": 40105, "message": "Access token is incorrect or has been revoked.", "request_id": "x"}),
    ("marketplaces/digistore24.json", "list_products", {}, "https://www.digistore24.com/api/call/listProducts",
     {"api_version": "1.2", "result": "error", "message": "The API key is invalid.", "code": 0}),
    ("jobs/saramin.json", "search", {"query": "python"}, "https://oapi.saramin.co.kr/job-search",
     {"code": 2, "message": "사용 불가능한 access-key 입니다. "}),
    ("ads/baidu_marketing.json", "list_campaigns", {"account_id": "1"}, "https://api.baidu.com/json/sms/service/CampaignService/getCampaign",
     {"header": {"desc": "failure", "failures": [{"code": 89406, "position": "_user", "message": "The access token you provided is invalidate."}], "oprs": 0, "succ": 0}}),
])
async def test_error_bodies_in_a_200_are_errors_not_empty_results(rel, verb, args, url, body):
    """Audit finding: these platforms answer HTTP 200 with an error body; without an envelope the tool reported success with no rows."""
    e = _entry(rel)
    a = e["adapter"]
    respx.route(url__startswith=url).mock(return_value=httpx.Response(200, json=body))
    if a["auth"].get("token_url"):  # a valid token, so the error comes from the API call itself
        respx.route(url__startswith=a["auth"]["token_url"]).mock(return_value=httpx.Response(200, json={
            "code": 0, "data": {"accessToken": "ACCESS-x", "refreshToken": "REFRESH-x", "expiresIn": 86400}}))
    creds = {f["name"]: "x" * 12 for f in a["auth"].get("fields", [])} | {f["name"]: "1234567" for f in a.get("config_fields", []) or []}
    res = await build_server(e, transport=Transport(a["base_url"], a["auth"], creds, 50, "test", envelope=a.get("envelope"))).call_tool(verb, args)
    assert res.is_error is True, res.structured_content
    assert res.structured_content["error"] in ("auth_error", "upstream_error")


def test_bfl_video_body_and_printful_catalog_params_follow_the_vendor_specs():
    """bfl: Flux3VideoT2VInputs forbids extra properties (no webhook_url); printful: GET /products takes only category_id."""
    video = _entry("builder_tools/bfl.json")["adapter"]["tools"]["generate_video"]
    assert "webhook_url" not in video["body"]
    products = _entry("ecommerce_suppliers/printful.json")["adapter"]["tools"]["list_products"]
    assert set(products["params"]) == {"category_id"} and "total" not in products["result"]
