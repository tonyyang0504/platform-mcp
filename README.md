# platform-mcp

MCP servers for the platform APIs behind real business work: job boards, freelance marketplaces, ad networks,
e-commerce channels and suppliers, messaging, social networks, sales data, trading venues, market data and car
listings. One evidence-only **catalog** (`catalog/`) describes each platform; one package, **platform-mcp-hub**,
serves any of them: `platform-mcp-hub serve <id>`. The Python package (PyPI) and the TypeScript package (npm) ship the
same runtime contract, the whole catalog and the same CLI.

## Quick start

From PyPI (`uvx` / `pip install platform-mcp-hub`) or npm (`npx platform-mcp-hub`):

```bash
uvx platform-mcp-hub list                    # every served platform (455), with its tools
uvx platform-mcp-hub describe reed           # tools, credentials (PLATFORM_MCP_REED_*), run commands
PLATFORM_MCP_REED_API_KEY=... uvx platform-mcp-hub serve reed            # stdio MCP server
uvx platform-mcp-hub serve reed --http --port 8000                      # Streamable HTTP on 127.0.0.1:8000/mcp
claude mcp add reed -e PLATFORM_MCP_REED_API_KEY=... -- uvx platform-mcp-hub serve reed
npx platform-mcp-hub serve reed              # the TypeScript build: identical tools
uvx platform-mcp-hub directory               # one server that searches the whole catalog (3,500 platforms)
```

From source:

```bash
uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve reed
# or in a checkout
git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp
uv run platform-mcp-hub serve reed
cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve reed
```

An id served in two categories needs the category: `platform-mcp-hub serve social/linkedin`. An entry you wrote
yourself runs the same way: `platform-mcp-hub serve --entry my_entry.json`, including a **generic** entry whose tools
come straight from an API's own operations (no category vocabulary; see `docs/ADAPTER_CONTRACT.md`).

## Principles

- **Evidence only.** Every tool maps to an endpoint documented on the platform's own developer pages, with the docs
  URL and the date it was verified. Nothing is guessed from a sibling API.
- **One verb vocabulary per category.** All job boards expose the same `search`, `get_posting`, `apply`,
  `list_messages`; all freelance marketplaces the same `search_postings`, `submit_bid`, `list_messages`, and so on.
- **Honest capabilities.** A verb a platform does not offer is not a tool (`not_offered` says why). Operations a
  platform's terms forbid are never automated.
- **Standard-first.** Current MCP revision, JSON Schema 2020-12 in and out, tool annotations on every tool, API
  failures as `isError` results, client-side rate limits, credentials from the environment, no token passthrough.
- **Same behaviour in both languages.** The Python and TypeScript runtimes pass the same contract tests; the parity
  test compares the tools of every served entry and the CLI answers of both builds.

## Layout

```
catalog/               the source of truth: <category>/<platform>.json, schema/vocab.json, index and directory snapshot
runtime/python/        platform_mcp_hub: runtime, CLI, directory server, lint, try/smoke/live-verify tools
runtime/typescript/    the npm package: runtime, CLI and directory server (same contract)
generators/python/     registry metadata per served entry (servers/<category>/<id>/server.json, manifest.json, README)
servers/               generated registry metadata (no code: every server is `platform-mcp-hub serve <id>`)
tools/                 gen_all (regenerate everything derived), build_directory, auth_audit, smoke_stdio
tests/                 contract tests per platform (both languages), runtime, security and CLI parity tests
docs/                  adapter contract, architecture, live verification and auth audit reports, security review
```

## Credentials and security

Credentials come only from `PLATFORM_MCP_<ID>_<FIELD>` environment variables (`describe` lists them); vendor
sandboxes are selected with `PLATFORM_MCP_<ID>_ENV`. Outbound requests are refused for private, loopback and
metadata addresses (connections are pinned to the vetted address), secrets are redacted from every message, catalog
text is sanitised before an MCP client sees it, and `--http` binds 127.0.0.1 unless you pass `--allow-remote` and set
`PLATFORM_MCP_HTTP_TOKEN`. See `SECURITY.md` and `docs/SECURITY_REVIEW_2026-10.md`.

## Limits (honest list)

- **Coverage.** 455 of about 3,500 catalogued platforms are served. The others carry a status record (gated or
  partner-only docs, upload-only access, an official vendor MCP server, or auth the runtime does not support yet).
- **Verification depth.** Keyless servers are live-verified (`docs/LIVE_VERIFICATION.md`, each entry's
  `live_check`). Servers that need credentials passed a credential-free audit (`docs/AUTH_AUDIT.md`): endpoints and
  specs were checked, but most have not been exercised with a real account. Write tools were never called live.
- **APIs change.** Entries cite the docs as they were on `verified_at`; vendors move endpoints and limits.
- **Terms are yours to respect.** Using a server means using the platform's API under its terms with your
  credentials. The catalog notes known restrictions; it is not legal advice.
- **TypeScript CLI** serves (`list`, `describe`, `serve`, `directory`); the authoring tools (`lint`, `try`, `smoke`,
  `verify`) are in the Python package.

## Related

The documentation-to-entry authoring tools that used to live here (the "forge") are now a separate project,
[api-to-mcp](https://github.com/tonyyang0504/api-to-mcp), which uses platform-mcp-hub as its runtime.

## Contributing

Pull requests are welcome: a new platform, a fix to an entry, runtime work. Read `CONTRIBUTING.md` (gates, DCO
sign-off) and `docs/ADAPTER_CONTRACT.md`. Security issues: `SECURITY.md`. Changes: `CHANGELOG.md`.

## Licence

Apache-2.0. See `LICENSE` and `NOTICE`.
