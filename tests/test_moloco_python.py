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

SPEC = json.loads((ROOT / "catalog" / "ads" / "moloco.json").read_text(encoding="utf-8"))
B = "https://api.moloco.cloud/cm/v1"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "mol-api-key-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


def _login():
    return respx.post(f"{B}/auth/tokens").mock(return_value=httpx.Response(200, json={"token": "MOLTOKEN", "token_type": "AUTH_TOKEN"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "list_campaigns", "get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_login_with_api_key_then_list_campaigns():
    login = _login()
    route = respx.get(f"{B}/campaigns").mock(return_value=httpx.Response(200, json={"campaigns": [
        {"id": "c1", "title": "UA US", "state": "ACTIVE", "currency": "USD", "enabling_state": "ENABLED", "schedule": {"start": "2026-09-01T00:00:00Z"}}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "acc1", "status": "ACTIVE"})
    assert res.is_error is False
    assert json.loads(login.calls[0].request.content) == {"api_key": "mol-api-key-secret"}
    assert route.calls[0].request.headers["Authorization"] == "Bearer MOLTOKEN"
    assert parse_qs(urlparse(str(route.calls[0].request.url)).query) == {"ad_account_id": ["acc1"], "states": ["ACTIVE"]}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"], c["start"]) == ("c1", "UA US", "ACTIVE", "2026-09-01T00:00:00Z")


@pytest.mark.asyncio
@respx.mock
async def test_get_report_posts_analytics_overview():
    _login()
    route = respx.post(f"{B}/analytics-overview").mock(return_value=httpx.Response(200, json={"rows": [
        {"date": "2026-09-01", "campaign": {"id": "c1", "title": "UA US"}, "metric": {"impressions": "1000", "clicks": "20", "installs": "4", "spend": 12.5}}]}))
    res = await _server().call_tool("get_report", {"account_id": "acc1", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    body = json.loads(route.calls[0].request.content)
    assert body["ad_account_id"] == "acc1" and body["date_range"] == {"start": "2026-09-01", "end": "2026-09-07"}
    assert body["dimensions"] == ["DATE", "CAMPAIGN_ID", "CAMPAIGN_TITLE"]
    r = res.structured_content["rows"][0]
    assert (r["campaign_id"], r["spend"], r["installs"]) == ("c1", 12.5, "4")


@pytest.mark.asyncio
@respx.mock
async def test_refused_login_does_not_leak_key():
    respx.post(f"{B}/auth/tokens").mock(return_value=httpx.Response(401, json={"message": "the given credential doesn't match mol-api-key-secret"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "mol-api-key-secret" not in json.dumps(res.structured_content)
