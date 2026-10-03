# Security policy

## Reporting a vulnerability

Please report security issues **privately** through GitHub Security Advisories: open this repository's **Security**
tab and choose **Report a vulnerability** (https://github.com/tonyyang0504/platform-mcp/security/advisories/new).
Do not open a public issue, pull request or discussion for a vulnerability.

Include what you found, how to reproduce it (an entry, a tool call, a request), the impact you expect and the version
or commit. You will get an acknowledgement within 7 days and a fix or a plan within 30 days for confirmed issues; we
coordinate disclosure with you and credit you in the advisory unless you prefer otherwise.

## Supported versions

| version | supported |
|---|---|
| 0.1.x (main) | yes |
| anything older | no |

## Scope

In scope: the Python and TypeScript runtimes (`platform-mcp-hub`), the CLI and directory server, the catalog lint and
verification tools, the release workflow, and catalog entries that would make a server act unsafely (for example an
endpoint that leaks credentials to another host).

Out of scope: vulnerabilities in the platforms' own APIs (report those to the vendor), and the consequences of running
a server with credentials you gave it (a server acts with exactly the permissions of those credentials; use the
narrowest key the platform offers).

## How the runtimes protect you

- Credentials only from `PLATFORM_MCP_<ID>_*` environment variables; every credential and minted token is redacted
  from errors and logs.
- Outbound requests to private, loopback, link-local and metadata addresses are refused, and connections are pinned to
  the vetted address (no DNS rebinding); catalog endpoints must be public https URLs (the lint enforces it).
- Catalog text (labels, notes, instructions) is sanitised before an MCP client sees it.
- `--http` binds 127.0.0.1; a non-loopback bind needs `--allow-remote` **and** a bearer token
  (`PLATFORM_MCP_HTTP_TOKEN`, 24+ characters).
- Releases are built in GitHub Actions and published with PyPI trusted publishing and npm provenance; no registry
  token is stored.

The October 2026 review and its regression tests: [`docs/SECURITY_REVIEW_2026-10.md`](docs/SECURITY_REVIEW_2026-10.md).
