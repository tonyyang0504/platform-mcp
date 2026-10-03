import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/we_work_remotely.json", import.meta.url), "utf8"));
const resp = (status, text, ct, extra = {}) => ({ status, headers: { get: (k) => ({ "content-type": ct, ...extra })[k.toLowerCase()] ?? null }, text: async () => text });

async function connect(handler, creds = {}) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); return handler(new URL(url), init); };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.log = log;
  return client;
}
const FEED = "https://weworkremotely.com/remote-jobs.rss";
const XML = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>Acme: DevOps Engineer</title><region>Anywhere in the World</region><country>United States</country><state></state><skills>DevOps, AWS, Terraform</skills><category>DevOps and Sysadmin</category><type>Full-Time</type><description>&lt;p&gt;Run our infra.&lt;/p&gt;</description><pubDate>Fri, 25 Sep 2026 00:33:21 +0000</pubDate><expires_at>Sun, 25 Oct 2026 00:33:21 +0000</expires_at><guid>https://weworkremotely.com/remote-jobs/acme-devops-engineer</guid><link>https://weworkremotely.com/remote-jobs/acme-devops-engineer</link></item><item><title>Beta: Designer</title><description>x</description><pubDate>Thu, 24 Sep 2026 00:00:00 +0000</pubDate><guid>https://weworkremotely.com/remote-jobs/beta-designer</guid><link>https://weworkremotely.com/remote-jobs/beta-designer</link></item></channel></rss>";

test("we_work_remotely: only search_postings is offered (wire)", async () => {
  const client = await connect(() => resp(200, "", "text/plain"));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
});

test("we_work_remotely: search_postings parses the RSS feed (main, wire)", async () => {
  const client = await connect(() => resp(200, XML, "application/rss+xml; charset=utf-8"));
  const res = await client.callTool({ name: "search_postings", arguments: {"query": "devops", "category": "DevOps"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings;
  assert.equal(p.length, 2);
  const expect = {"id": "https://weworkremotely.com/remote-jobs/acme-devops-engineer", "title": "Acme: DevOps Engineer", "url": "https://weworkremotely.com/remote-jobs/acme-devops-engineer", "posted_at": "Fri, 25 Sep 2026 00:33:21 +0000", "description": "<p>Run our infra.</p>"};
  for (const [k, v] of Object.entries(expect)) assert.equal(p[0][k], v, k);
  assert.equal(p[0].raw["skills"], "DevOps, AWS, Terraform");
  const seen = client.log[0];
  assert.equal(seen.url.href.split("?")[0], FEED);
  assert.equal(seen.init.method, "GET");
  assert.deepEqual(Object.fromEntries(seen.url.searchParams), {});
});

test("we_work_remotely: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => resp(429, "", "text/plain", { "retry-after": "30" }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
