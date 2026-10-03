import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402


def _form(req):
    return {k: v[0] for k, v in parse_qs(req.content.decode()).items()}


async def _names(server):
    return sorted(t.name for t in await server.list_tools())

SPEC = json.loads((ROOT / "catalog" / "ads" / "tiktok_creator_marketplace.json").read_text(encoding="utf-8"))
A = "https://business-api.tiktok.com/open_api/v1.3"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "ttotoken123", "app_secret": "ttosecret9", "app_id": "7000"}, 50, "test", envelope=SPEC["adapter"]["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["list_campaigns", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_campaigns_use_access_token_header_and_page_size_cap():
    route = respx.get(f"{A}/tto/tcm/campaign/").mock(return_value=httpx.Response(200, json={"code": 0, "message": "OK", "data": {
        "campaigns": [{"campaign_id": "7300", "campaign_name": "Launch", "brand_name": "Acme", "campaign_type": "CAMPAIGN"}], "page_info": {"page": 1, "page_size": 5, "total_number": 1}}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "tcm1", "limit": 50})
    req = route.calls[0].request
    assert req.headers["Access-Token"] == "ttotoken123"
    assert dict(req.url.params) == {"tto_tcm_account_id": "tcm1", "page": "1", "page_size": "5"}
    assert res.structured_content["campaigns"][0]["id"] == "7300" and res.structured_content["total"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_nonzero_code_is_an_error_and_secret_scrubbed():
    route = respx.get(f"{A}/tto/oauth2/tcm/").mock(return_value=httpx.Response(200, json={"code": 40105, "message": "Access token is invalid: ttotoken123", "data": {}}))
    res = await _server().call_tool("me", {})
    assert route.calls[0].request.url.params["app_id"] == "7000"
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "ttotoken123" not in json.dumps(res.structured_content)
