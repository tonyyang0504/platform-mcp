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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "tradera.json").read_text(encoding="utf-8"))
CREDS = {"app_id": "1234", "app_key": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_get_item_sends_app_headers():
    route = respx.get("https://api.tradera.com/v4/items/567890").mock(return_value=httpx.Response(200, json={
        "id": 567890, "shortDescription": "Volvo 240 GL 1989", "longDescription": "Fin bil", "buyItNowPrice": 25000, "itemLink": "https://www.tradera.com/item/1/567890", "startDate": "2026-09-20T10:00:00"}))
    res = await _server().call_tool("get_listing", {"listing_id": "567890"})
    sc = res.structured_content
    assert res.is_error is False and sc["id"] == "567890" and sc["title"] == "Volvo 240 GL 1989" and sc["price"] == 25000 and sc["currency"] == "SEK"
    h = route.calls.last.request.headers
    assert h["X-App-Id"] == "1234" and h["X-App-Key"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
