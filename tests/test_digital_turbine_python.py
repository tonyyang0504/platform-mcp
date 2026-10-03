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

SPEC = json.loads((ROOT / "catalog" / "ads" / "digital_turbine.json").read_text(encoding="utf-8"))
G = "https://acp-edge-api.fyber.com/graphql"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"management_api_token": "dt-mgmt-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list_is_update_budget_only():
    assert {t.name for t in await _server().list_tools()} == {"update_budget", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_mutation_variables_and_api_key():
    route = respx.post(G).mock(return_value=httpx.Response(200, json={"data": {"offerCampaignBulkUpdateBids": {"errors": []}}}))
    res = await _server().call_tool("update_budget", {"campaign_id": "12", "daily_budget": 2.3})
    assert res.is_error is False and res.structured_content["status"] == "submitted" and res.structured_content["errors"] == []
    req = route.calls[0].request
    assert req.headers["x-api-key"] == "dt-mgmt-secret"
    body = json.loads(req.content)
    assert body["variables"] == {"offerCmsId": "12", "bidsList": [{"dailyBudget": "2.3"}]}
    assert body["operationName"] == "campaignBulkBidsManage" and "offerCampaignBulkUpdateBids" in body["query"]


@pytest.mark.asyncio
@respx.mock
async def test_graphql_error_without_data_is_an_error():
    respx.post(G).mock(return_value=httpx.Response(200, json={"data": None, "errors": [{"message": "offer not found"}]}))
    res = await _server().call_tool("update_budget", {"campaign_id": "99", "daily_budget": 5})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_does_not_leak():
    respx.post(G).mock(return_value=httpx.Response(403, text="forbidden for dt-mgmt-secret"))
    res = await _server().call_tool("update_budget", {"campaign_id": "12", "daily_budget": 5})
    assert res.structured_content["error"] == "auth_error" and "dt-mgmt-secret" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_sends_graphql_boolean_offer_enabled():
    route = respx.post("https://acp-edge-api.fyber.com/graphql").mock(return_value=httpx.Response(200, json={"data": {"offerCampaignBulkUpdateBids": {"errors": []}}}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "12", "action": "pause"})
    assert res.is_error is False and res.structured_content["status"] == "submitted"
    body = json.loads(route.calls[0].request.content)
    assert body["variables"] == {"offerCmsId": "12", "offerEnabled": False, "bidsList": []}
    assert "offerEnabled: $offerEnabled" in body["query"]
