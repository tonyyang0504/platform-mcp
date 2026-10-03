import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/aws_partner_network.json", import.meta.url), "utf8"));
const CREDS = { access_key_id: "AKIDEXAMPLE", secret_access_key: "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY" };
const sha = (s) => crypto.createHash("sha256").update(s).digest("hex");
const hm = (k, s) => crypto.createHmac("sha256", k).update(s).digest();

async function connect(handler, log) {
  const f = async (url, init) => { log.push({ url: new URL(url), init }); return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify(handler(new URL(url), init)) }; };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("aws_partner_network: SigV4-signed awsJson1_0 call with X-Amz-Target", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    const log = [];
    const c = await connect(() => ({ EngagementInvitationSummaries: [{ Id: "engi-0123456789abc", EngagementTitle: "Migration", SenderCompanyName: "AWS" }], NextToken: "t2" }), log);
    const res = await c.callTool({ name: "search_postings", arguments: { limit: 5 } });
    assert.equal(res.isError, false);
    assert.equal(res.structuredContent.postings[0].id, "engi-0123456789abc");
    assert.equal(res.structuredContent.next_cursor, "t2");
    const { url, init } = log[0];
    assert.equal(url.href, "https://partnercentral-selling.us-east-1.api.aws/");
    assert.equal(init.method, "POST");
    assert.equal(init.headers["X-Amz-Target"], "AWSPartnerCentralSelling.ListEngagementInvitations");
    assert.equal(init.headers["Content-Type"], "application/x-amz-json-1.0");
    assert.deepEqual(JSON.parse(init.body), { Catalog: "AWS", ParticipantType: "RECEIVER", MaxResults: 5 });
    const amz = "20260925T020000Z";
    assert.equal(init.headers["X-Amz-Date"], amz);
    const canonical = ["POST", "/", "", `host:partnercentral-selling.us-east-1.api.aws\nx-amz-date:${amz}\n`, "host;x-amz-date", sha(init.body)].join("\n");
    const scope = "20260925/us-east-1/partnercentral-selling/aws4_request";
    let k = Buffer.from("AWS4" + CREDS.secret_access_key);
    for (const part of ["20260925", "us-east-1", "partnercentral-selling", "aws4_request"]) k = hm(k, part);
    const sig = crypto.createHmac("sha256", k).update(["AWS4-HMAC-SHA256", amz, scope, sha(canonical)].join("\n")).digest("hex");
    assert.equal(init.headers.Authorization, `AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/${scope}, SignedHeaders=host;x-amz-date, Signature=${sig}`);
  } finally { Date.now = realNow; }
});

test("aws_partner_network: accept invitation then poll the task", async () => {
  const log = [];
  let n = 0;
  const c = await connect(() => (n++ === 0 ? { TaskId: "task-0123456789abc", TaskStatus: "IN_PROGRESS" } : { TaskSummaries: [{ TaskId: "task-0123456789abc", TaskStatus: "COMPLETE" }] }), log);
  const bid = await c.callTool({ name: "submit_bid", arguments: { posting_id: "engi-0123456789abc", amount: 0 } });
  assert.equal(bid.structuredContent.bid_id, "task-0123456789abc");
  assert.equal(log[0].init.headers["X-Amz-Target"], "AWSPartnerCentralSelling.StartEngagementByAcceptingInvitationTask");
  const st = await c.callTool({ name: "bid_status", arguments: { bid_id: "task-0123456789abc" } });
  assert.equal(st.structuredContent.status, "COMPLETE");
  assert.deepEqual(JSON.parse(log[1].init.body), { Catalog: "AWS", TaskIdentifier: ["task-0123456789abc"] });
});
