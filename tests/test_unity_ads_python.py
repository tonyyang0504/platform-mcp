import base64
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

SPEC = json.loads((ROOT / "catalog" / "ads" / "unity_ads.json").read_text(encoding="utf-8"))
B = "https://services.api.unity.com/advertise/v1/organizations/org123"
APP = "5f9f1b9b9c9d440000a1b2c3"
CMP = "6a0f1b9b9c9d440000d4e5f6"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"key_id": "unity-key", "secret_key": "unity-secret-xyz", "organization_id": "org123", "campaign_set_id": APP}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "list_campaigns", "update_budget", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_filter_enabled_and_basic_auth():
    route = respx.get(f"{B}/apps/{APP}/campaigns").mock(return_value=httpx.Response(200, json={"total": 1, "results": [
        {"id": CMP, "name": "US CPI", "goal": "installs", "enabled": True, "scheduleStart": "2026-09-01T00:00:00Z", "scheduleEnd": None}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": APP, "status": "active"})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"unity-key:unity-secret-xyz").decode()
    assert parse_qs(urlparse(str(req.url)).query) == {"filter[enabled]": ["true"]}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["enabled"], c["start"]) == (CMP, "US CPI", True, "2026-09-01T00:00:00Z")


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_patches_daily_string_on_configured_app():
    route = respx.patch(f"{B}/apps/{APP}/campaigns/{CMP}/budget").mock(return_value=httpx.Response(200, json={"total": "0", "daily": "750.5", "dailySpent": "0"}))
    res = await _server().call_tool("update_budget", {"campaign_id": CMP, "daily_budget": 750.5})
    assert res.is_error is False and res.structured_content["status"] == "updated" and res.structured_content["daily"] == "750.5"
    assert json.loads(route.calls[0].request.content) == {"daily": "750.5"}


@pytest.mark.asyncio
@respx.mock
async def test_refused_service_account_does_not_leak():
    respx.get(f"{B}/apps").mock(return_value=httpx.Response(403, json={"title": "Forbidden", "detail": "unity-secret-xyz lacks role"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "unity-secret-xyz" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_patches_enabled_boolean():
    route = respx.patch(f"{B}/apps/{APP}/campaigns/{CMP}").mock(return_value=httpx.Response(200, json={"id": CMP, "enabled": True}))
    res = await _server().call_tool("pause_resume", {"campaign_id": CMP, "action": "resume"})
    assert res.is_error is False and res.structured_content["enabled"] is True
    assert json.loads(route.calls[0].request.content) == {"enabled": True}
