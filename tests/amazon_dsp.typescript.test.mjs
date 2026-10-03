import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
const form = (body) => Object.fromEntries(new URLSearchParams(body));
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/amazon_dsp.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_AMAZON_DSP_CLIENT_ID: "amzn1.cid", PLATFORM_MCP_AMAZON_DSP_CLIENT_SECRET: "lwasecret", PLATFORM_MCP_AMAZON_DSP_REFRESH_TOKEN: "Atzr|refresh", PLATFORM_MCP_AMAZON_DSP_API_HOST: "advertising-api-eu.amazon.com", PLATFORM_MCP_AMAZON_DSP_PROFILE_ID: "4001" });

test("amazon_dsp list_accounts: /dsp/advertisers startIndex/count (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "api.amazon.com") return { body: { access_token: "Atza|D", expires_in: 3600 } };
    return { body: { totalResults: 1, response: [{ advertiserId: "47", name: "Adv", currency: "EUR" }] } };
  });
  const res = await client.callTool({ name: "list_accounts", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen[1].url.pathname, "/dsp/advertisers");
  assert.equal(seen[1].url.searchParams.get("count"), "25");
  assert.equal(seen[1].init.headers["Amazon-Advertising-API-ClientId"], "amzn1.cid");
  assert.equal(res.structuredContent.accounts[0].currency, "EUR");
});
