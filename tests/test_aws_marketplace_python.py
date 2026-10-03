import hashlib
import hmac
import json
import sys
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "aws_marketplace.json").read_text(encoding="utf-8"))
CREDS = {"access_key_id": "AKIDMPEXAMPLE", "secret_access_key": "mpSecret/EXAMPLE+abcdef", "entity_type": "SaaSProduct"}
CAT = "catalog.marketplace.us-east-1.amazonaws.com"
AGR = "agreement-marketplace.us-east-1.amazonaws.com"
AMZ = "20260925T020000Z"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _auth(method, host, path, query, body):
    names = ["host", "x-amz-date"]
    canonical = "\n".join([method, path, query, f"host:{host}\nx-amz-date:{AMZ}\n", ";".join(names), hashlib.sha256(body).hexdigest()])
    scope = f"{AMZ[:8]}/us-east-1/aws-marketplace/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", AMZ, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = ("AWS4" + CREDS["secret_access_key"]).encode()
    for part in (AMZ[:8], "us-east-1", "aws-marketplace", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    return f"AWS4-HMAC-SHA256 Credential={CREDS['access_key_id']}/{scope}, SignedHeaders=host;x-amz-date, Signature={hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()}"


@pytest.fixture
def frozen(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)


@pytest.mark.asyncio
@respx.mock
async def test_list_entities_is_signed_and_cursor_paginated(frozen):
    route = respx.post(f"https://{CAT}/ListEntities").mock(return_value=httpx.Response(200, json={"EntitySummaryList": [
        {"EntityId": "prod-abc123", "Name": "Acme SaaS", "Visibility": "Public", "EntityType": "SaaSProduct", "LastModifiedDate": "2026-09-01T10:00:00Z"}], "NextToken": "NT-2"}))
    res = await _server().call_tool("list_products", {"limit": 10})
    p = res.structured_content["products"][0]
    assert p["id"] == "prod-abc123" and p["name"] == "Acme SaaS" and p["status"] == "Public" and res.structured_content["next_cursor"] == "NT-2"
    req = route.calls[0].request
    assert json.loads(req.content) == {"Catalog": "AWSMarketplace", "EntityType": "SaaSProduct", "OwnershipType": "SELF", "MaxResults": 10}
    assert req.headers["Authorization"] == _auth("POST", CAT, "/ListEntities", "", req.content)


@pytest.mark.asyncio
@respx.mock
async def test_describe_entity_signs_the_canonical_query(frozen):
    route = respx.get(url__startswith=f"https://{CAT}/DescribeEntity").mock(return_value=httpx.Response(200, json={
        "EntityIdentifier": "prod-abc123@7", "EntityType": "SaaSProduct@1.0", "LastModifiedDate": "2026-09-01T10:00:00Z",
        "DetailsDocument": {"Description": {"ProductTitle": "Acme SaaS", "ShortDescription": "Analytics", "Visibility": "Public"}}}))
    res = await _server().call_tool("get_product", {"product_id": "prod-abc123"})
    assert res.structured_content["name"] == "Acme SaaS" and res.structured_content["id"] == "prod-abc123@7"
    req = route.calls[0].request
    assert req.url.params["catalog"] == "AWSMarketplace" and req.url.params["entityId"] == "prod-abc123"
    assert req.headers["Authorization"] == _auth("GET", CAT, "/DescribeEntity", "catalog=AWSMarketplace&entityId=prod-abc123", b"")


@pytest.mark.asyncio
@respx.mock
async def test_search_agreements_uses_the_json_target(frozen):
    route = respx.post(f"https://{AGR}/").mock(return_value=httpx.Response(200, json={"agreementViewSummaries": [
        {"agreementId": "agmt-111", "status": "ACTIVE", "acceptanceTime": 1788000000, "acceptor": {"accountId": "123456789012"}, "proposalSummary": {"offerId": "offer-9", "resources": [{"id": "prod-abc123", "type": "SaaSProduct"}]}}]}))
    res = await _server().call_tool("list_sales", {"limit": 5})
    s = res.structured_content["sales"][0]
    assert s["id"] == "agmt-111" and s["product_id"] == "prod-abc123" and s["buyer_account_id"] == "123456789012"
    req = route.calls[0].request
    assert req.headers["X-Amz-Target"] == "AWSMPCommerceService_v20200301.SearchAgreements" and req.headers["Content-Type"] == "application/x-amz-json-1.0"
    assert json.loads(req.content) == {"catalog": "AWSMarketplace", "filters": [{"name": "PartyType", "values": ["Proposer"]}, {"name": "AgreementType", "values": ["PurchaseAgreement"]}], "maxResults": 5}
    assert req.headers["Authorization"] == _auth("POST", AGR, "/", "", req.content)


@pytest.mark.asyncio
@respx.mock
async def test_list_refunds_and_access_denied(frozen):
    route = respx.post(f"https://{AGR}/").mock(side_effect=[
        httpx.Response(200, json={"items": [{"billingAdjustmentRequestId": "ba-1", "agreementId": "agmt-111", "adjustmentAmount": "10.5", "currencyCode": "USD", "status": "PENDING", "createdAt": 1788000000}]}),
        httpx.Response(403, json={"__type": "AccessDeniedException", "message": "not authorized"})])
    s = _server()
    r = await s.call_tool("list_refunds", {"since": "2026-09-01"})
    assert r.structured_content["refunds"][0]["id"] == "ba-1" and r.structured_content["refunds"][0]["sale_id"] == "agmt-111"
    assert json.loads(route.calls[0].request.content)["createdAfter"] == 1788220800
    assert route.calls[0].request.headers["X-Amz-Target"].endswith(".ListBillingAdjustmentRequests")
    e = await s.call_tool("list_sales", {})
    assert e.is_error is True and e.structured_content["error"] == "auth_error" and CREDS["secret_access_key"] not in json.dumps(e.structured_content)
