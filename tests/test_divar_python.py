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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "divar.json").read_text(encoding="utf-8"))
API = "https://open-api.divar.ir"
CREDS = {"api_key": "divar-key-0123456789"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_finder_search_posts_the_car_query():
    route = respx.post(API + "/v2/open-platform/finder/post").mock(return_value=httpx.Response(200, json={"posts": [
        {"token": "wZFdL0Vm", "category": "light", "last_modified_at": "2024-11-26T11:59:25.794428Z", "city": "tehran", "title": "چانگان cs55",
         "price": {"mode": "مقطوع", "value": "100000000"}, "vehicles_fields": {"usage": "10000"}}]}))
    res = await _server().call_tool("search_listings", {"location": "tehran", "model": "Pride 111 EX", "year_min": 1400, "year_max": 1403, "mileage_max": 100000})
    assert res.is_error is False, res.structured_content
    row = res.structured_content["listings"][0]
    assert row["id"] == "wZFdL0Vm" and row["location"] == "tehran"
    req = route.calls.last.request
    assert req.headers["x-api-key"] == "divar-key-0123456789"
    assert json.loads(req.content) == {"category": "light", "city": "tehran", "query": {"brand_model": ["Pride 111 EX"], "production_year": {"min": 1400, "max": 1403}, "usage": {"max": 100000}}}


@pytest.mark.asyncio
@respx.mock
async def test_get_post_maps_data():
    respx.get(API + "/v1/open-platform/finder/post/AZir15UU").mock(return_value=httpx.Response(200, json={
        "token": "AZir15UU", "category": "light", "city": "tehran", "data": {"title": "پژو ۲۰۶", "description": "سالم", "price": {"mode": "مقطوع", "value": 1100000}, "images": ["https://s101.divarcdn.com/a.jpg"]}}))
    res = await _server().call_tool("get_listing", {"listing_id": "AZir15UU"})
    sc = res.structured_content
    assert res.is_error is False and sc["price"] == 1100000 and sc["images"] == ["https://s101.divarcdn.com/a.jpg"] and sc["title"] == "پژو ۲۰۶"
