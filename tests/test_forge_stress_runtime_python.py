"""Runtime regression cases from the forge stress test (2026-10). The same cases
(tests/fixtures/forge_stress_cases.json) run in tests/forge_stress_runtime.typescript.test.mjs, so both runtimes are
held to identical answers."""
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

CASES = json.loads((ROOT / "tests" / "fixtures" / "forge_stress_cases.json").read_text(encoding="utf-8"))


def _get(obj, path):
    for part in path.split("."):
        if part == "length":
            return len(obj)
        obj = obj[int(part)] if isinstance(obj, list) else obj.get(part)
    return obj


def _response(r: dict) -> httpx.Response:
    headers = r.get("headers") or {}
    if "bytes_b64" in r:
        return httpx.Response(r["status"], headers=headers, content=base64.b64decode(r["bytes_b64"]))
    if "text" in r:
        return httpx.Response(r["status"], headers=headers, content=r["text"].encode("utf-8"))
    return httpx.Response(r["status"], headers=headers, content=json.dumps(r["body"], ensure_ascii=False).encode("utf-8"))


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
async def test_case(case):
    spec = {"id": "stress_case", "category": case["category"], "label": "case", "adapter": case["adapter"]}
    a = spec["adapter"]
    with respx.mock(assert_all_called=False) as mock:
        route = mock.route(host="api.example.test").mock(side_effect=[_response(r) for r in case["responses"]])
        server = build_server(spec, transport=Transport(a["base_url"], a["auth"], {}, 1000, "test", envelope=a.get("envelope")))
        res = await server.call_tool(case["verb"], case["args"])
    out = res.structured_content
    if "error" in case:
        assert res.is_error, out
        err = case["error"]
        assert out["error"] == err["kind"], out
        if "message" in err:
            assert out["message"] == err["message"]
        if "contains" in err:
            assert err["contains"] in out["message"]
    else:
        assert not res.is_error, out
    for path, want in (case.get("expect") or {}).items():
        assert _get(out, path) == want, (path, out)
    want = case.get("request") or {}
    if "count" in want:
        assert route.call_count == want["count"]
    if "path" in want or "query" in want:
        req = route.calls.last.request
        if "path" in want:
            assert req.url.raw_path.decode().split("?")[0] == want["path"]
        for k, v in (want.get("query") or {}).items():
            assert req.url.params[k] == v
