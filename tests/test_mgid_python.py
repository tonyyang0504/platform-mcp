import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "mgid.json").read_text(encoding="utf-8"))
B = "https://api.mgid.com/v1"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_token": "mgid0123456789abcdef0123456789ab", "client_id": "555"}, 50, "test")
    return build_server(SPEC, transport=t)


def _q(req):
    return {k: v[0] for k, v in parse_qs(urlparse(str(req.url)).query).items()}


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "update_budget", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_me_reads_client_wallet_with_bearer():
    route = respx.get(f"{B}/clients/555").mock(return_value=httpx.Response(200, json={"id": "555", "timezone": "UTC", "wallet": {"balance": 10000, "credit": 0, "income": 50000, "currency": "USD"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["wallet"]["currency"] == "USD"
    assert route.calls[0].request.headers["Authorization"] == "Bearer mgid0123456789abcdef0123456789ab"


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_and_pause_send_query_parameters():
    route = respx.patch(f"{B}/goodhits/clients/555/campaigns/777").mock(return_value=httpx.Response(200, json={"id": 777}))
    res = await _server().call_tool("update_budget", {"campaign_id": "777", "daily_budget": 25.5})
    assert res.is_error is False and res.structured_content["status"] == "updated" and res.structured_content["campaign_id"] == "777"
    assert _q(route.calls[0].request) == {"limitType": "budget_limits", "dailyLimit": "25.5"}
    await _server().call_tool("pause_resume", {"campaign_id": "777", "action": "pause"})
    assert _q(route.calls[1].request) == {"whetherToBlockByClient": "1"}
    bad = await _server().call_tool("pause_resume", {"campaign_id": "777", "action": "stop"})
    assert bad.is_error is True


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_does_not_leak():
    respx.get(f"{B}/clients/555").mock(return_value=httpx.Response(401, json={"errors": ["[INVALID_TOKEN mgid0123456789abcdef0123456789ab]"]}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "mgid0123456789abcdef0123456789ab" not in json.dumps(res.structured_content)
