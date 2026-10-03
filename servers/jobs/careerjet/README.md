# Careerjet MCP server

Category: **jobs** · Docs: https://www.careerjet.com/partners/api/ · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/careerjet.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /query` (https://www.careerjet.com/partners/api/)
- `search` — `GET /query` (https://www.careerjet.com/partners/api/)
- ~~`get_posting`~~ not offered: No per-job endpoint is documented ('job_details (excerpt + redirect URL)' come from the search hit).
- ~~`apply`~~ not offered: Page: 'Aggregator — applying happens on the source site (assist)'; robots.txt disallows /apply/ and /apply2/.
- ~~`list_messages`~~ not offered: No messaging API; only the search endpoint is documented.

## Credentials

- `PLATFORM_MCP_CAREERJET_API_KEY` — Careerjet publisher API key (free publisher sign-up at https://www.careerjet.com/partners/api/); sent as the HTTP Basic user name with an empty password.
- `PLATFORM_MCP_CAREERJET_USER_IP` — The end user's IP address, required by Careerjet as the user_ip query parameter on every call (403 'Missing param user_ip or user_agent' otherwise).
- `PLATFORM_MCP_CAREERJET_USER_AGENT` — The end user's browser user agent, required by Careerjet as the user_agent query parameter on every call.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve careerjet   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve careerjet
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve careerjet   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/careerjet-mcp`. Python and TypeScript serve identical tools.
