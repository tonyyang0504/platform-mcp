import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "bcb_sgs");

test("bcb dd/mm/aaaa dates both ways, 406 and the 200 HTML page for an unknown code (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => {
    if (u.pathname.includes("sgs.433")) return { body: [{ data: "01/01/2026", valor: "0.33" }, { data: "01/02/2026", valor: "-0.32" }] };
    if (u.pathname.includes("sgs.1/")) return { status: 406, body: { error: "O sistema aceita uma janela de consulta de, no máximo, 10 anos" } };
    return { body: '<?xml version="1.0" encoding="pt-br"?><!DOCTYPE html><html><head><title>Requisição inválida!</title></head></html>', type: "text/html; charset=utf-8" };
  });
  const pts = (await call("get_series", { series_id: "433", start: "2026-01-01", end: "2026-09-30" })).structuredContent.points;
  assert.deepEqual(pts.map((p) => [p.time, p.value]), [["2026-01-01", 0.33], ["2026-02-01", -0.32]]);
  assert.equal(log[0].url.searchParams.get("dataInicial"), "01/01/2026");
  assert.equal((await call("get_series", { series_id: "1" })).structuredContent.error, "invalid_input");
  const bad = (await call("get_series", { series_id: "999999999", start: "2026-01-01" })).structuredContent;
  assert.equal(bad.error, "not_found"); assert.match(bad.message, /Requisição inválida/);
});
