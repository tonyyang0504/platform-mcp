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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "autostrefa_mx.json").read_text(encoding="utf-8"))
API = "https://autostrefa.mx/api/public"
CAR = {"id": 83890829, "slug": "land-rover-defender-2024", "titulo": "Land Rover Defender X-Dynamic SE 90 2024", "marca": "Land Rover",
       "modelo": "Defender X-Dynamic SE 90", "año": 2024, "precio": 1849900, "kilometraje": 35035, "ubicacion": "Reynosa",
       "url": "https://trefa.mx/autos/land-rover-defender-2024", "descripcion": "Llega a TREFA"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_inventory_search_without_credentials():
    route = respx.get(url__startswith=API + "/inventory").mock(return_value=httpx.Response(200, json={"success": True, "data": [CAR], "meta": {"total": 45, "page": 1, "per_page": 10, "total_pages": 5}}))
    res = await _server().call_tool("search_listings", {"make": "Land Rover", "price_max": 2000000, "year_min": 2020, "limit": 10})
    assert res.is_error is False, res.structured_content
    row = res.structured_content["listings"][0]
    assert row["id"] == "83890829" and row["year"] == 2024 and row["price"] == 1849900 and row["currency"] == "MXN" and res.structured_content["total"] == 45
    req = route.calls.last.request
    assert "Authorization" not in req.headers
    q = req.url.params
    assert q["marca"] == "Land Rover" and q["precio_max"] == "2000000" and q["ano_min"] == "2020" and q["per_page"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_detail_by_slug_and_envelope_errors():
    respx.get(API + "/inventory/land-rover-defender-2024").mock(return_value=httpx.Response(200, json={"success": True, "data": CAR}))
    res = await _server().call_tool("get_listing", {"listing_id": "land-rover-defender-2024"})
    assert res.is_error is False and res.structured_content["description"] == "Llega a TREFA"
    respx.get(API + "/inventory/nope").mock(return_value=httpx.Response(200, json={"success": False, "data": None, "error": "Vehiculo no encontrado"}))
    bad = await _server().call_tool("get_listing", {"listing_id": "nope"})
    assert bad.is_error is True
