"""Banco Central do Brasil SGS (forge stress test 2026-10, Portuguese docs): dd/mm/aaaa dates both ways, 406 for a
missing window, a 200 HTML page for an unknown code (error_kinds applied to unparsed bodies)."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "bcb_sgs.json").read_text(encoding="utf-8"))
BASE = "https://api.bcb.gov.br/dados/serie"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_dates_both_ways():
    route = respx.get(f"{BASE}/bcdata.sgs.433/dados").mock(return_value=httpx.Response(200, json=[{"data": "01/01/2026", "valor": "0.33"}, {"data": "01/02/2026", "valor": "-0.32"}]))
    pts = (await _server().call_tool("get_series", {"series_id": "433", "start": "2026-01-01", "end": "2026-09-30"})).structured_content["points"]
    assert [(p["time"], p["value"]) for p in pts] == [("2026-01-01", 0.33), ("2026-02-01", -0.32)]
    q = route.calls.last.request.url.params
    assert (q["formato"], q["dataInicial"], q["dataFinal"]) == ("json", "01/01/2026", "30/09/2026")


@pytest.mark.asyncio
@respx.mock
async def test_window_required_and_unknown_code():
    respx.get(f"{BASE}/bcdata.sgs.1/dados").mock(return_value=httpx.Response(406, json={"error": "O sistema aceita uma janela de consulta de, no máximo, 10 anos em séries de periodicidade diária"}))
    r = await _server().call_tool("get_series", {"series_id": "1"})
    assert r.is_error and r.structured_content["error"] == "invalid_input"
    respx.get(f"{BASE}/bcdata.sgs.999999999/dados").mock(return_value=httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"},
        text='<?xml version="1.0" encoding="pt-br"?><!DOCTYPE html><html><head><title>Requisição inválida!</title></head><body></body></html>'))
    r = await _server().call_tool("get_series", {"series_id": "999999999", "start": "2026-01-01"})
    assert r.is_error and r.structured_content["error"] == "not_found" and "Requisição inválida" in r.structured_content["message"]
