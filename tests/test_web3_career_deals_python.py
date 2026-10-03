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

SPEC = json.loads((ROOT / "catalog" / "deals" / "web3_career.json").read_text(encoding="utf-8"))
URL = "https://web3.career/api/v1"
TOKEN = "w3c-token-abcdef0123456789"

# documented example response (docs.bondex.app OpenAPI, opened 2026-09-25): [string, string, Job[]]
JOB = {"id": "abc123", "title": "Senior Smart Contract Engineer", "company": "ExampleDAO", "location": "Remote", "remote": True,
       "description": "<p>…</p>", "tags": ["solidity", "ethereum"], "apply_url": "https://web3.career/senior-smart-contract-engineer-exampledao?ref=abc",
       "url": "https://web3.career/senior-smart-contract-engineer-exampledao", "salary": "$150k - $200k", "postedAt": "2025-03-15"}


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds if creds is not None else {"token": TOKEN}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered():
    assert [t.name for t in await _server().list_tools()] == ["search_postings"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_token_tag_limit_and_reads_element_two():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=["ok", "v1", [JOB]]))
    res = await _server().call_tool("search_postings", {"query": "solidity dev", "category": "solidity", "limit": 5, "min_budget": 1})
    assert res.is_error is False
    assert dict(route.calls.last.request.url.params) == {"token": TOKEN, "tag": "solidity", "limit": "5", "show_description": "true"}
    p = res.structured_content["postings"][0]
    assert p["id"] == "abc123" and p["buyer"] == "ExampleDAO" and p["url"].endswith("?ref=abc") and p["skills"] == ["solidity", "ethereum"]
    assert p["posted_at"] == "2025-03-15" and p["raw"]["salary"] == "$150k - $200k"


@pytest.mark.asyncio
@respx.mock
async def test_invalid_token_is_auth_error_without_leaking_it():
    respx.get(URL).mock(return_value=httpx.Response(401, json={"error": f"invalid token {TOKEN}"}))
    res = await _server().call_tool("search_postings", {"category": "rust"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert TOKEN not in json.dumps(res.structured_content)
