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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "poe.json").read_text(encoding="utf-8"))
BOT = {"handle": "MyCustomBot", "description": "A custom bot", "is_private": True,
       "api_bot_settings": {"model_name": "my-model", "base_url": "https://api.example.com/v1", "api_type": "chat_completions_api",
                            "pricing": {"prompt": "0.00003", "completion": "0.00006"}}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "sk_test_POEKEY123"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_bot_listing_is_offered():
    assert sorted(t.name for t in await _server().list_tools()) == ["list_products", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_list_products_maps_bots_with_bearer_key():
    route = respx.get("https://api.poe.com/bots").mock(return_value=httpx.Response(200, json={"bots": [BOT]}))
    res = await _server().call_tool("list_products", {"limit": 5})
    assert res.is_error is False, res.structured_content
    p = res.structured_content["products"][0]
    assert p["id"] == "MyCustomBot" and p.get("price") is None and p["raw"]["api_bot_settings"]["pricing"]["prompt"] == "0.00003" and p["description"] == "A custom bot"
    assert route.calls.last.request.headers["Authorization"] == "Bearer sk_test_POEKEY123"
    assert dict(route.calls.last.request.url.params) == {}


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_an_auth_error():
    respx.get("https://api.poe.com/bots").mock(return_value=httpx.Response(401, json={"error": "invalid key sk_test_POEKEY123"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "sk_test_POEKEY123" not in json.dumps(res.structured_content)
