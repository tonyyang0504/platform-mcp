import base64
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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "twodehands.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "tdh-client", "client_secret": "tdh-secret-0123456789"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_search_goes_to_the_2dehands_platform():
    tok = respx.post("https://auth.2dehands.be/accounts/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "tdh-access", "expires_in": 86400}))
    route = respx.get(url__startswith="https://api.2dehands.be/v1/search").mock(return_value=httpx.Response(200, json={"_embedded": {"mp:search-result": [{"itemId": "m1", "title": "Opel Corsa"}]}, "totalCount": 1}))
    res = await _server().call_tool("search_listings", {"query": "corsa"})
    assert res.is_error is False and res.structured_content["listings"][0]["id"] == "m1"
    assert route.calls.last.request.headers["Authorization"] == "Bearer tdh-access" and tok.called
    assert "categoryId" not in route.calls.last.request.url.params
