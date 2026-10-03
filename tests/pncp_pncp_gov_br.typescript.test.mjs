import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/pncp_pncp_gov_br.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const ROW = { orgaoEntidade: { razaoSocial: "MINISTERIO DA FAZENDA" }, objetoCompra: "Manutenção de balança", numeroControlePNCP: "00394460000141-1-000224/2022", valorTotalEstimado: 37553.33, dataEncerramentoProposta: "2030-05-10T07:59:59", linkSistemaOrigem: "https://www.comprasnet.gov.br/x" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("pncp: search sends dataFinal, modality and paging (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { data: [ROW], totalRegistros: 1 } }; });
  const res = await client.callTool({ name: "search_postings", arguments: { category: "6", page: 3, limit: 20 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta");
  assert.equal(seen.searchParams.get("dataFinal"), "20991231");
  assert.equal(seen.searchParams.get("codigoModalidadeContratacao"), "6");
  assert.equal(seen.searchParams.get("pagina"), "3");
  assert.equal(seen.searchParams.get("tamanhoPagina"), "20");
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "00394460000141-1-000224/2022");
  assert.equal(p.budget_max, 37553.33);
});

test("pncp: a 400 is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 400, body: { message: "must be greater than or equal to 10" } }));
  const res = await client.callTool({ name: "search_postings", arguments: { limit: 5 } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "invalid_input");
});
