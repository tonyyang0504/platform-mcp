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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "mercedes_benz_gebrauchtwagen.json").read_text(encoding="utf-8"))
API = "https://api.mercedes-benz.com/vehicle_specifications_fleet/v1"
CREDS = {"api_key": "mb-key-0123456789abcdef", "locale": "de_DE"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))


@pytest.mark.asyncio
async def test_only_decode_vin_is_served():
    assert [t.name for t in await _server().list_tools()] == ["decode_vin"]


@pytest.mark.asyncio
@respx.mock
async def test_decode_vin_maps_vehicle_data():
    route = respx.get(url__startswith=API + "/vehicles/WDD2951321F999999").mock(return_value=httpx.Response(200, json={"vehicleData": {
        "brand": {"code": "095", "text": "Mercedes-Benz"}, "modelName": "EQE", "longType": "Mercedes-AMG EQE 43 4MATIC", "body": {"code": "9", "text": "Sports Tourer"},
        "enginetype": {"code": "7", "text": "Elektroantrieb"}, "fuel": {"code": "E", "text": "Elektro"}, "modelYear": "802"}}))
    res = await _server().call_tool("decode_vin", {"vin": "WDD2951321F999999"})
    sc = res.structured_content
    assert res.is_error is False and sc["make"] == "Mercedes-Benz" and sc["model"] == "EQE" and sc["trim"] == "Mercedes-AMG EQE 43 4MATIC" and sc["fuel"] == "Elektro"
    req = route.calls.last.request
    assert req.headers["x-api-key"] == "mb-key-0123456789abcdef" and req.url.params["locale"] == "de_DE" and req.url.params["payloadNullValues"] == "false"
