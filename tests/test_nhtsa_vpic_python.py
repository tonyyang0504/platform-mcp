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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "nhtsa_vpic.json").read_text(encoding="utf-8"))
URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/"
MSG = "Results returned successfully. NOTE: Any missing decoded values should be interpreted as NHTSA does not have data on the specific variable."


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_only_decode_vin():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["decode_vin"] and tools[0].annotations.read_only_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_decode_vin_maps_the_flat_record():
    route = respx.get(URL + "1HGCM82633A004352").mock(return_value=httpx.Response(200, json={"Count": 1, "Message": MSG, "SearchCriteria": "VIN(s): 1HGCM82633A004352", "Results": [
        {"VIN": "1HGCM82633A004352", "Make": "HONDA", "Model": "Accord", "ModelYear": "2003", "Trim": "EX-V6", "BodyClass": "Coupe", "EngineModel": "J30A4",
         "EngineConfiguration": "V-Shaped", "DisplacementL": "2.998832712", "FuelTypePrimary": "Gasoline", "ErrorCode": "0", "ErrorText": "0 - VIN decoded clean. Check Digit (9th position) is correct"}]}))
    res = await _server().call_tool("decode_vin", {"vin": "1HGCM82633A004352"})
    assert res.is_error is False and route.calls.last.request.url.params["format"] == "json"
    v = res.structured_content
    assert (v["vin"], v["make"], v["model"], v["year"], v["trim"], v["body"], v["engine"], v["fuel"]) == ("1HGCM82633A004352", "HONDA", "Accord", 2003, "EX-V6", "Coupe", "J30A4", "Gasoline")


@pytest.mark.asyncio
@respx.mock
async def test_undecodable_vin_is_an_error_with_nhtsas_text():
    respx.get(URL + "zz-bad").mock(return_value=httpx.Response(200, json={"Count": 1, "Message": MSG, "Results": [
        {"VIN": "zz-bad", "Make": "", "Model": "", "ModelYear": "", "ErrorCode": "6,7,400", "ErrorText": "6 - Incomplete VIN; 7 - Manufacturer is not registered; 400 - Invalid Characters Present"}]}))
    res = await _server().call_tool("decode_vin", {"vin": "zz-bad"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
    assert res.structured_content["message"].startswith("6 - Incomplete VIN")
