import assert from "node:assert/strict";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, data } from "../runtime/typescript/dist/directory.js";

async function connect() {
  const server = buildServer();
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}
const call = async (client, name, args = {}) => { const r = await client.callTool({ name, arguments: args }); return { ...r, payload: r.structuredContent ?? JSON.parse(r.content[0].text) }; };

test("directory tools are read-only and list categories with verbs", async () => {
  const client = await connect();
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["describe_platform", "list_categories", "list_platforms", "search_capabilities"]);
  for (const t of tools) assert.equal(t.annotations.readOnlyHint, true);
  const { payload } = await call(client, "list_categories");
  const jobs = payload.categories.find((c) => c.category === "jobs");
  assert.ok(jobs.platforms > 200 && jobs.served >= 9 && jobs.verbs.includes("search"));
  assert.equal(payload.categories.reduce((n, c) => n + c.platforms, 0), data().platforms.length);
});

test("list, describe and search agree with the snapshot", async () => {
  const client = await connect();
  const list = (await call(client, "list_platforms", { category: "jobs", served_only: true, limit: 3 })).payload;
  assert.ok(list.total >= 9 && list.items.length === 3 && list.items.every((i) => i.served && i.category === "jobs"));
  const reed = (await call(client, "describe_platform", { platform_id: "reed" })).payload;
  assert.deepEqual(reed.tools, ["get_posting", "me", "search"]);
  assert.equal(reed.install.status, undefined); assert.equal(reed.install.from_source, undefined); // platform-mcp-hub is published
  assert.equal(reed.install.serve, "platform-mcp-hub serve reed");
  assert.equal(reed.install.npx, "npx -y platform-mcp-hub serve reed"); assert.equal(reed.install.uvx, "uvx platform-mcp-hub serve reed");
  assert.equal(reed.serve, "reed"); assert.equal(reed.registry_name, "io.github.tonyyang0504/reed-mcp");
  assert.equal(reed.credentials[0].env, "PLATFORM_MCP_REED_API_KEY");
  const missing = await call(client, "describe_platform", { platform_id: "nope" });
  assert.equal(missing.isError, true);
  assert.equal(missing.payload.error, "not_found");
  const s = (await call(client, "search_capabilities", { capability: "search", category: "jobs" })).payload;
  assert.ok(s.total >= 9 && s.items[0].served === true && s.items[0].matched === "tool");
});
