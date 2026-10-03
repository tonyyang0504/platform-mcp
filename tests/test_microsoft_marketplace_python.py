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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "microsoft_marketplace.json").read_text(encoding="utf-8"))
TOKEN = "https://login.microsoftonline.com/tenant-123/oauth2/v2.0/token"
BASE = "https://graph.microsoft.com/rp/product-ingestion"
CREDS = {"client_id": "app-1", "client_secret": "SECRETentra", "tenant_id": "tenant-123"}
PRODUCT = {"$schema": "https://schema.mp.microsoft.com/schema/product/2022-03-01-preview3", "id": "product/1234-abcd",
           "identity": {"externalID": "contoso-resize"}, "type": "softwareAsAService", "alias": "Contoso Image Resizing Service"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(CREDS), 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_product", "list_products", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_token_url_carries_the_tenant_and_products_are_listed():
    tok = respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "GRAPH-AT", "expires_in": 3599}))
    route = respx.get(url__startswith=BASE + "/product").mock(return_value=httpx.Response(200, json={"value": [PRODUCT]}))
    res = await _server().call_tool("list_products", {"limit": 10, "cursor": "CT-2"})
    assert res.is_error is False, res.structured_content
    assert res.structured_content["products"][0] == {**res.structured_content["products"][0], "id": "product/1234-abcd", "name": "Contoso Image Resizing Service"}
    form = dict(x.split("=", 1) for x in tok.calls.last.request.content.decode().split("&"))
    assert form["grant_type"] == "client_credentials" and form["client_id"] == "app-1" and form["scope"] == "https%3A%2F%2Fgraph.microsoft.com%2F.default"
    req = route.calls.last.request
    assert req.url.params["$version"] == "2022-03-01-preview3" and req.url.params["$maxpagesize"] == "10" and req.url.params["continuationToken"] == "CT-2"
    assert "$version=" in str(req.url) and req.headers["Authorization"] == "Bearer GRAPH-AT"


@pytest.mark.asyncio
@respx.mock
async def test_get_product_by_durable_id():
    respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "GRAPH-AT", "expires_in": 3599}))
    route = respx.get(url__startswith=BASE + "/product/1234-abcd").mock(return_value=httpx.Response(200, json=PRODUCT))
    res = await _server().call_tool("get_product", {"product_id": "product/1234-abcd"})
    assert res.is_error is False and res.structured_content["raw"]["identity"]["externalID"] == "contoso-resize"
    assert route.calls.last.request.url.params["$version"] == "2022-03-01-preview3"


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_is_an_auth_error():
    respx.post(TOKEN).mock(return_value=httpx.Response(401, json={"error": "invalid_client"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
