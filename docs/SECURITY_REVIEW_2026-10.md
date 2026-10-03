# Security review 2026-10 — forge and shared MCP runtime

> **After the review (0.1.0 restructure).** The forge was split out of this repository with its tests (SR-07, SR-08,
> SR-12, SR-13, SR-14 and the forge half of SR-19 are covered there). The 455 per-platform packages were replaced by one
> package, `platform-mcp-hub` (`platform-mcp-hub serve <id>`), so SR-01's surface (catalog text in generated code) is
> gone: only registry metadata (JSON, Markdown) is generated. SR-15's publish workflow was replaced by
> `.github/workflows/release.yml` with PyPI trusted publishing and npm provenance (no stored tokens). SR-17 now concerns
> one name, `platform-mcp-hub`, on PyPI and npm (`docs/RELEASE_CHECKLIST.md`). File paths below are as they were on the
> review date.

Date: 2026-10-01. Scope: `forge/`, `runtime/python/platform_mcp_hub`, `runtime/typescript/src`, `generators/`,
`skills/mcp-forge`, `agents/mcp-forge.md`, `.claude-plugin`, `.mcp.json`, `tools/*.py`, `.github/workflows`.
Method: adversarial read of every path from "API document / tool argument" to "network, file system, generated
code, secrets"; each finding got a failing regression test first, then the fix, in both runtimes where it applies.

Regression tests: `tests/test_security_python.py` / `tests/security.typescript.test.mjs` and (second round)
`tests/test_security2_python.py` / `tests/security2.typescript.test.mjs` (the same cases for the two runtimes),
`tests/test_security_forge_python.py`, `tests/test_security_generators_python.py`, and the shared tables
`tests/fixtures/netguard_cases.json`, `tests/fixtures/security2_cases.json` and `tests/fixtures/sanitize_cases.json`.

A second round on the same day closed what code can close before open-sourcing: SR-18, SR-14 (agent tool list), the
DNS-rebinding residual (now SR-19), the downstream prompt-injection residual (now SR-20) and the code side of SR-17.

## Findings

| ID | Severity | Finding | Status | Fix commit |
|----|----------|---------|--------|------------|
| SR-01 | High | Catalog strings became code in generated packages | Fixed | a3279308 |
| SR-02 | High | SSRF through multipart `file:<arg>` downloads (cloud metadata) | Fixed | ce4c025d |
| SR-03 | Medium | Tool arguments spliced raw into the URL path (traversal, query/fragment injection) | Fixed | ce4c025d |
| SR-04 | Medium | TypeScript followed API/token/login redirects with credential headers attached | Fixed | ce4c025d |
| SR-05 | Medium | 401 re-login retried with the stale token (query, path, body, cookie, signature) | Fixed | ce4c025d |
| SR-06 | Medium | TypeScript Streamable HTTP built a new transport per request (rotated refresh token lost, no rate limit) | Fixed | ce4c025d |
| SR-07 | Medium | Forge `ingest_openapi` SSRF (any host, redirects followed, unbounded download) | Fixed | 94227749 |
| SR-08 | Medium | Forge `ingest_openapi` read any local file and quoted it in YAML errors | Fixed | 94227749 |
| SR-09 | Low | Redaction missed encoded secrets and Basic header values | Fixed | ce4c025d |
| SR-10 | Low | Refresh-token state file: fixed temp name, followed planted symlinks | Fixed | ce4c025d |
| SR-11 | Low | A cursor the platform hands back unchanged looped forever | Fixed | ce4c025d |
| SR-12 | Medium | `try_tool` / `live_verify` would call (and print) internal hosts named by an entry or a plan | Fixed | 94227749, a3279308 |
| SR-13 | Low | The forge's automatic `npm ci` ran dependency install scripts | Fixed | 94227749 |
| SR-14 | Medium | No prompt-injection containment in the skill/agent rules; agent held Bash and WebFetch | Fixed | 94227749, e10f2609 |
| SR-15 | Medium | Publish workflow: registry tokens workflow-wide, input interpolated into shell, unpinned publisher | Fixed | 395de99e |
| SR-16 | Medium | `rate_per_second` exceeded (about 2x after waits; TS concurrent bursts unbounded) | Fixed | a8ef9373 |
| SR-17 | High | Package names advertised to users are unclaimed on npm and PyPI | **Mitigated in code; claiming the names is open** (operator) | c7262962 |
| SR-18 | Low | `--http` servers have no authentication; a non-loopback bind exposes the operator's credentials | Fixed | 3f2f4f9c |
| SR-19 | Medium | DNS rebinding between the address check and the connection (downloads, forge fetches) | Fixed | 62f45b9e |
| SR-20 | Medium | Catalog `instructions`/`note`/label text reached MCP clients unfiltered (downstream prompt injection) | Fixed | a7f42bdf |

Totals: 3 high (2 fixed, 1 mitigated with an operator action open), 12 medium (all fixed), 5 low (all fixed).

## Details

**SR-01 (High) — code injection through the catalog into generated packages.** `generators/python/gen.py` wrote
`label` raw into a `"""docstring"""` in `__init__.py`; a label such as `X"""\nimport os; os.system(...)\n"""` ran on
import — in `test_server`'s smoke, in `live_verify`, and on every user's machine after `uvx`. The same label (or
`version`) was written raw into `pyproject.toml`, where it could add tables such as a hatch build hook (code at
`pip install` time), and a label with a line terminator (`\n`, `\r`, U+2028) escaped the `//` comment of the
TypeScript `server.ts`. The label comes from the document the forge agent reads, so a hostile API page could pick
it. Fix: both generators refuse `id`/`category` outside `[a-z0-9_]{1,60}` (also closes `servers/<cat>/<id>` path
traversal) and a non-`MAJOR.MINOR.PATCH` version, JSON-escape the label for Python/TOML and strip line terminators
for TypeScript; the lint rejects control characters in labels and non-semver versions. Output for the existing
catalog is byte-identical (`gen_all` produces no diff). Test: `test_a_hostile_label_stays_data_in_both_packages`
(the PWNED marker was written before the fix).

**SR-02 (High) — SSRF through `file:` downloads.** A multipart tool (`generate_image`, listing uploads) downloads
the URL in a tool argument and uploads the bytes to the vendor. Nothing restricted the target and redirects were
followed: a model steered by any text it read can pass `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>`
(or an intranet URL) and the server, running on a cloud host, fetches the credentials and uploads them where the
attacker can read them (a public product image). Fix (both runtimes, `netguard.py`/`netguard.ts`): http(s) only;
every resolved address must be public (loopback, RFC 1918, link-local/metadata, CGNAT, multicast, reserved,
documentation, and IPv4 inside mapped/NAT64/6to4 IPv6 are refused); unresolvable hosts are refused; redirects are
followed manually (max 5), each hop re-checked; body capped by `PLATFORM_MCP_MAX_DOWNLOAD_MB` (default 50).
`PLATFORM_MCP_ALLOW_PRIVATE_URLS=1` is the operator's opt-out.

**SR-03 (Medium) — path argument injection.** `{id}` was replaced with the raw argument. `id = "../../admin/users"`
moved a read-only tool (auto-approved by many clients) to another endpoint of the vendor API with the user's
credentials; `7?delete=true` or `#` added a query or cut the path. In TypeScript `String.replace` additionally
interpreted `$&`/`` $` `` in the argument. Fix: values are percent-encoded outside RFC 3986 pchar and `/`, existing
`%XX` escapes are kept (pre-encoded LinkedIn URNs), and any `.`/`..` segment — also as `%2E`, which WHATWG URL (Node
fetch) resolves — is an `invalid_input` error before anything is sent. `/` is kept because real ids carry it
(OpenCorporates `gb/00102498`, Hugging Face `google/gemma-2b`, Microsoft Marketplace `product/…`).

**SR-04 (Medium) — redirects with credentials (TypeScript).** Node `fetch` follows redirects by default and strips
only `Authorization`/`Cookie` across origins; `X-Api-Key`, `extra_headers`, signature headers and AWS SigV4 headers
went to whatever host a 3xx named. The Python runtime never followed redirects, so the runtimes also disagreed.
Fix: every API, token and login request uses `redirect: "manual"`, as in Python.

**SR-05 (Medium) — 401 refresh path.** After a 401 both runtimes minted a new token but re-sent the already-built
URL and body, updating only the Authorization header; a token carried as `token_param` (WeCom, Shopee), in the path
(`{access_token}`), in the body (`token_body_path`), in a cookie or inside a signature was the old one, so the retry
failed with `auth_error` until the process restarted. Fix: the request is rebuilt from scratch after the re-login
(multipart downloads are reused, not fetched twice).

**SR-06 (Medium) — TypeScript Streamable HTTP.** `serveHttp(() => buildServer(spec))` created a new adapter and
transport per HTTP request: a login/token mint per call, no effective rate limit or cache, and for single-use
rotating refresh tokens (Allegro, Mercado Libre) the rotated token was lost after the first request unless
`PLATFORM_MCP_STATE_DIR` was set — the next request presented a revoked token. Fix: `serverFactory` shares one
adapter/transport across per-request servers (Python already built one server).

**SR-07 (Medium) — forge spec fetch SSRF.** `ingest_openapi` fetched any `http(s)` URL with `follow_redirects=True`
and read the whole body before checking its size. The agent ingests the `spec_links` the tool extracts from a page,
so a hostile page could make the forge (on a workstation or a cloud host) request metadata endpoints or intranet
services (blind GET, status oracle, YAML-error snippets). Fix: the same netguard check on every hop, manual
redirects, streamed body with the 25 MB cap; `blocked_url` error.

**SR-08 (Medium) — local file read and disclosure.** Any path (or `file://`) was read; YAML parse errors returned
PyYAML's context snippet. `ingest_openapi("~/.aws/credentials")` returned `aws_access_key_id = AKIA…` to the model,
which a prompt-injected agent could then send anywhere with WebFetch. Fix: local specs must be `.json`/`.yaml`/`.yml`,
not under any hidden path component (`~/.aws`, `~/.ssh`, `.env`, `~/.config`), at most 25 MB; YAML errors give the
problem, line and column only (quoted tokens elided).

**SR-09 (Low) — redaction gaps.** Secrets were redacted only verbatim: an error body echoing the query string
(`api_key=p%40ss…`), a form body (`+` for spaces) or the `Authorization: Basic <base64>` header leaked them, and
`Authorization: Bearer X` redacted the word `Bearer` instead of the value. Fix: URL- and form-encoded variants are
registered with every secret; the Basic value (also of the OAuth token request) is registered; the scheme word is
kept and the value redacted.

**SR-10 (Low) — state file.** Rotated refresh tokens were written to a fixed temp name (`<id>.tmp` in Python,
`<id>.json.tmp` in TS) with `O_TRUNC`/`writeFileSync`, following a planted symlink (overwrite of another file with
the token) and keeping the mode of a pre-existing temp file. Fix: an exclusively created random temp file (0600)
and an atomic rename; a created state directory is 0700.

**SR-11 (Low) — cursor loop.** A platform answering `next = <the cursor it was given>` made clients page forever.
Fix: such a `next_cursor` is `null` in both runtimes.

**SR-12 (Medium) — live tools against internal hosts.** An entry written from a hostile document may name
`https://10.0.0.5/…` (or a plan may set `config.BASE_URL`); `try_tool` prints the raw response, so it would read
intranet HTTPS services into the model's context. Fix: `tools/egress_guard.py` resolves every host the effective
adapter would call (base URL after `_ENV`/`_BASE_URL` and plan config, absolute tool paths, token and login URLs)
and `try_tool` (`blocked_host`) and `live_verify` refuse non-public ones; the lint refuses non-https credentialed
URLs and localhost/private IP literals in the catalog.

**SR-13 (Low) — install scripts in the auto-build.** `npm ci` in the forge's automatic TypeScript build ran
dependency lifecycle scripts (esbuild's postinstall through dev tooling). The build only needs `tsc`. Fix:
`npm ci --ignore-scripts` in the forge, its printed fix command and CI.

**SR-14 (Medium) — prompt injection.** The skill and agent said nothing about untrusted content while the agent
held Bash, Write, Edit, WebFetch and every forge tool. Round 1: skill rule 6, the agent and the forge server
instructions state that documentation is data, never instructions, and forbid bypassing `blocked_url`/`blocked_host`;
the tool-level guards (SR-07, SR-08, SR-12, SR-01) hold even when the model is fooled. Round 2: the agent has **no
Bash and no WebFetch**. A new forge tool `read_docs` reads documentation pages through the guarded, pinned fetcher
(public hosts only, redirects re-checked, optional r.jina.ai reader with the target checked as well) and labels the
text untrusted; every gate already runs through forge tools. Narrowing Bash with permission patterns was tried and
is not possible from the plugin: with Claude Code 2.1.286 a `Bash(git status:*)` entry in an agent's `tools` became
plain Bash (an `echo … > file` ran), and `permissions` in a plugin's `settings.json` were ignored (a denied
`touch` ran). Verified with the plugin loader as in FORGE_VERIFICATION.md (`claude -p --plugin-dir <copy> --agent
platform-mcp-forge:mcp-forge --allowedTools "Bash,WebFetch,…"`): the session exposed exactly Read, Write, Edit,
WebSearch, Skill, Glob, Grep and the 12 forge tools; the requested `touch` and WebFetch were impossible (no file was
created); `catalog_search` and `read_docs` worked live. For sessions run in a checkout, `.claude/settings.json`
allowlists only the gate commands.

**SR-15 (Medium) — publish workflow.** `PYPI_TOKEN`/`NPM_TOKEN` were workflow-level env, readable by every step
including `npm install`/`npm run build` (third-party lifecycle scripts) and an `mcp-publisher` binary downloaded from
`releases/latest` without verification; `workflow_dispatch` input was interpolated into shell (`${{ }}` script
injection). Fix: tokens only in the publish steps, inputs via env and validated against existing servers,
`--ignore-scripts`, `mcp-publisher` v1.8.1 pinned by SHA-256.

**SR-16 (Medium) — rate limiting.** After a wait the bucket kept its pre-sleep timestamp, so the next caller was
credited the slept time again (≈2× `rate_per_second` in both runtimes); the TypeScript bucket had no lock, so
concurrent calls slept the same interval and fired together (20 requests at 10/s all sent within ~100 ms).
Exceeding documented limits gets users' API keys throttled or banned. Fix: refill from the end of a wait; TS
bucket serialised.

**SR-17 (High, mitigated; operator action open) — unclaimed package names.** Every generated `server.json`, MCPB manifest and README tells
users to run `uvx platform-mcp-<id>` or `npx @platform-mcp/<id>`, and the generated packages depend on
`platform-mcp-core` / `@platform-mcp/core`. On 2026-10-01 the npm scope `platform-mcp` does not exist and none of
these PyPI/npm names are registered: whoever registers them first ships code to every user who follows the docs.
Code side (c7262962): `catalog/schema/release.json` (`"published": false`) makes every generated README and the
directory server's `install` hints (both builds) say "unpublished — install from source" with checkout commands
instead of `uvx`/`npx`/`pip install`; `docs/RELEASE_CHECKLIST.md` lists the operator's steps (claim the npm
organisation and every PyPI name, trusted publishing, no MCPB bundles before then) before flipping the flag. Nothing
was registered. Open: the operator must claim the names.

**SR-18 (Low) — unauthenticated HTTP mode.** `--http` served every tool with the operator's credentials and no
authentication; `--host 0.0.0.0` exposed the account to anyone who could reach the port. Fix (both runtimes): a
non-loopback host is refused (exit 2) unless `--allow-remote` AND `PLATFORM_MCP_HTTP_TOKEN` (≥ 24 characters) are
both given; whenever the token is set, every request needs `Authorization: Bearer <token>` (constant-time
comparison, 401 before anything is served). The TypeScript `serveHttp` resolves with the server (port 0 works).

**SR-19 (Medium) — DNS rebinding.** Round 1 resolved and checked the host, then the HTTP client resolved it again, so
a zero-TTL domain could answer public for the check and 127.0.0.1/169.254.169.254 for the connection. Fix: the
guard returns the vetted addresses and the caller connects to one of them (first IPv4 preferred). Python puts the IP
in the URL and keeps the `Host` header and `sni_hostname`, so TLS still verifies the certificate against the host
name; TypeScript uses `node:http(s)` with a fixed `lookup`, the original `Host` and `servername` (no new dependency,
undici is not needed). Applies to multipart `file:` downloads in both runtimes and to the forge's spec and
documentation fetches; every redirect hop is re-checked and re-pinned. Tests drive a rebinding resolver (public, then
loopback) and a local server reached through a name that never resolves.

**SR-20 (Medium) — catalog text reaching clients.** Server `instructions`, tool `note` (appended to the description)
and the label (in the server title) went to every MCP client verbatim; a client's model treats them as trusted tool
documentation, and an entry may have been written from a hostile document. Fix (both runtimes, identical tables):
invisible and bidi-control characters removed, control characters and line separators turned into spaces,
whitespace collapsed, well-known injection markers (`ignore previous instructions`, `<system>`, `<|im_start|>`,
`[INST]`, `BEGIN SYSTEM PROMPT`, `you are now a…`, `new instructions:` …) replaced with `[removed]`, lengths capped
(label 120, note 1500, instructions 2000). The lint reports the same problems as errors; the current catalog lints
clean. Marker matching is heuristic: it removes the common forms, not every phrasing.

## Checked, no finding

- **Response cache and tenants:** the cache lives in one transport, which holds one credential set from the
  process environment; there is no per-request credential input, so a cache keyed without credentials cannot
  serve one tenant's response to another. Failures and envelope errors are never cached. Still true with SR-06's
  shared transport.
- **Workspace and `save_entry`:** ids and categories are `^[a-z0-9_]{2,60}$` and categories must be vocabulary
  categories before any path is built; `catalog_get`'s glob uses the validated id.
- **`test_server`/`doctor` commands:** argv lists, never a shell; install commands are printed, never executed.
- **Environment separation:** sandbox refresh tokens are stored under `<id>.<env>.json`; the `_BASE_URL` override is
  https-only, never echoed and registered as a secret.
- **Error classification and retries:** no retry other than the single 401 re-login; `Retry-After` is passed
  through; messages are scrubbed.
- **auth_audit:** fetches only its own hard-coded vendor URLs; YAML uses a SafeLoader subclass.

## Residual risk

- **Rebinding on catalog hosts:** `try_tool`/`live_verify` check the entry's hosts before starting a server, but the
  generated server then connects to catalog hosts itself (not pinned); the lint forbids loopback/private IP literals
  and the hosts come from reviewed catalog entries.
- **Path ids with `/`:** kept for real ids, so an argument can still add segments under the tool's own path prefix
  (never `..`, a query or a fragment). Servers that decode `%2F`/`%2E` themselves are outside our control.
- **Injection markers are heuristic** (SR-20): unusual phrasings pass; catalog text is still reviewed in pull requests.
- **The agent keeps WebSearch** (search queries leave the machine) and Write/Edit within the workspace; `test_server`
  runs the contract tests the agent wrote (by design).
- **Registry names** (SR-17) stay open until the operator claims them; MCPB manifests still name `uvx <name>`.
- **Numbered paging** still relies on the platform honouring the page parameter; a platform that ignores it and
  reports no total returns the same full page forever (cursor loops are fixed, SR-11).
- **Workspace trust:** the forge executes the workspace's `tools/` and installs its lockfile; point it only at a
  checkout you trust.

## Gates

Local, worktree at the final commit of each round: catalog lint (0 errors), `tools/gen_all.py` (no diff), Python
tests, TypeScript tests, installed-package stdio smoke (reed, directory, forge wheels), `tools/build_directory.py`.
CI on GitHub: round 1 green at fe0581d9 (run 36859580063); round 2 see the commit that updates this file.
