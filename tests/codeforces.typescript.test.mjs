import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/competitions/codeforces.json", import.meta.url), "utf8"));
const resp = (status, body, type = "application/json") => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" && body !== undefined ? type : null) }, text: async () => (body === undefined ? "" : typeof body === "string" ? body : JSON.stringify(body)) });

async function connect(creds, handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url), init, log.length); return resp(r.status ?? 200, r.body, r.type); };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fetcher, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}
const hdr = (init, name) => { const h = init.headers ?? {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

const CONTESTS = { status: "OK", result: [
  { id: 2261, name: "Round A", type: "CF", phase: "BEFORE", startTimeSeconds: 1792247700 },
  { id: 2273, name: "Round B", type: "CF", phase: "BEFORE", startTimeSeconds: 1791743700 },
  { id: 566, name: "VK Cup 2015 - Finals, online mirror", type: "CF", phase: "FINISHED", startTimeSeconds: 1438273200 }] };

test("codeforces discover pages locally with url and ISO start (wire)", async () => {
  const { client } = await connect({}, () => ({ body: CONTESTS }));
  const s = (await client.callTool({ name: "discover", arguments: { limit: 2 } })).structuredContent;
  assert.deepEqual(s.competitions.map((c) => c.id), ["2261", "2273"]);
  assert.deepEqual([s.competitions[0].url, s.competitions[0].starts_at, s.total, s.next_page], ["https://codeforces.com/contest/2261", "2026-10-17T14:35:00Z", 3, 2]);
});

test("codeforces standings send only contestId; FAILED envelopes are errors (wire)", async () => {
  const { client, log } = await connect({}, (u) => (u.pathname.endsWith("contest.list")
    ? { body: { status: "FAILED", comment: "Call limit exceeded" } }
    : { body: { status: "OK", result: { contest: { id: 566, name: "VK Cup", phase: "FINISHED", startTimeSeconds: 1438273200 }, rows: [
        { party: { members: [{ handle: "tourist" }] }, rank: 1, points: 3504.0 }, { party: { members: [{ handle: "a" }], teamName: "Team AB" }, rank: 2, points: 3000.5 }] } } }));
  const s = (await client.callTool({ name: "standings", arguments: { competition_id: "566", limit: 1 } })).structuredContent;
  assert.deepEqual(s.standings.map((r) => [r.rank, r.team, r.score]), [[1, "tourist", 3504]]);
  assert.equal(s.next_page, 2);
  assert.deepEqual([...log[0].url.searchParams.keys()], ["contestId"]);
  const f = await client.callTool({ name: "discover", arguments: {} });
  assert.equal(f.isError, true);
  assert.equal(f.structuredContent.error, "rate_limited");
});

test("codeforces discover filters locally by title, kind and status (wire)", async () => {
  const { client } = await connect({}, () => ({ body: CONTESTS }));
  const ids = async (args) => (await client.callTool({ name: "discover", arguments: args })).structuredContent.competitions.map((c) => c.id);
  assert.deepEqual(await ids({ status: "completed" }), ["566"]);
  assert.deepEqual(await ids({ kind: "design" }), []);
  assert.deepEqual(await ids({ query: "VK CUP", kind: "coding" }), ["566"]);
});

test("codeforces competition then standings pages download the ranklist once; unknown contest is not_found (wire)", async () => {
  const STANDINGS = { status: "OK", result: { contest: { id: 566, name: "VK Cup 2015 - Finals, online mirror", phase: "FINISHED", startTimeSeconds: 1438273200 }, rows: [
    { party: { members: [{ handle: "tourist" }] }, rank: 1, points: 3504 }, { party: { members: [{ handle: "a" }], teamName: "Team AB" }, rank: 2, points: 3000.5 }, { party: { members: [{ handle: "c" }] }, rank: 3, points: 2100 }] } };
  const { client, log } = await connect({}, (u) => (u.searchParams.get("contestId") === "99999999" ? { status: 400, body: { status: "FAILED", comment: "contestId: Contest with id 99999999 not found" } } : { body: STANDINGS }));
  const c = (await client.callTool({ name: "get_competition", arguments: { competition_id: "566" } })).structuredContent;
  const p1 = (await client.callTool({ name: "standings", arguments: { competition_id: "566", limit: 2 } })).structuredContent;
  const p2 = (await client.callTool({ name: "standings", arguments: { competition_id: "566", limit: 2, page: 2 } })).structuredContent;
  assert.deepEqual([c.title, p1.standings.map((r) => r.rank), p2.standings.map((r) => r.rank), p1.next_page, log.length], ["VK Cup 2015 - Finals, online mirror", [1, 2], [3], 2, 1]);
  const bad = await client.callTool({ name: "get_competition", arguments: { competition_id: "99999999" } });
  assert.deepEqual([bad.isError, bad.structuredContent.error], [true, "not_found"]);
});
