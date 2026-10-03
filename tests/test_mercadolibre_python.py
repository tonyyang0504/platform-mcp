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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "mercadolibre.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "123", "client_secret": "ml-client-secret", "refresh_token": "TG-ml-refresh-1"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_get_listing_reads_a_vehicle_item_with_a_refreshed_token():
    respx.post("https://api.mercadolibre.com/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "APP_USR-ml-access", "expires_in": 21600, "refresh_token": "TG-ml-refresh-2"}))
    route = respx.get("https://api.mercadolibre.com/items/MLB1045563828").mock(return_value=httpx.Response(200, json={
        "id": "MLB1045563828", "title": "Volkswagen Gol 1.0", "category_id": "MLB1744", "price": 45000, "currency_id": "BRL", "condition": "used",
        "permalink": "https://carro.mercadolivre.com.br/MLB-1045563828", "date_created": "2026-09-01T12:00:00.000Z"}))
    res = await _server().call_tool("get_listing", {"listing_id": "MLB1045563828"})
    sc = res.structured_content
    assert res.is_error is False and sc["id"] == "MLB1045563828" and sc["price"] == 45000 and sc["currency"] == "BRL" and sc["url"].endswith("MLB-1045563828")
    assert route.calls.last.request.headers["Authorization"] == "Bearer APP_USR-ml-access"


@pytest.mark.asyncio
async def test_tools_are_me_and_get_listing():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_listing", "me"]
