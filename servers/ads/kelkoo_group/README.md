# Kelkoo Group MCP server

Category: **ads** · Docs: https://docs.kelkoogroup.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/kelkoo_group.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /my-campaigns` (https://docs.kelkoogroup.com/for-advertisers/merchant-statistics-api/merchant-statistics-resources)
- `list_campaigns` — `GET /my-campaigns` (https://docs.kelkoogroup.com/for-advertisers/merchant-statistics-api/merchant-statistics-resources)
- `get_report` — `GET /category/{campaign_id}` (https://docs.kelkoogroup.com/for-advertisers/merchant-statistics-api/merchant-statistics-resources)
- ~~`list_accounts`~~ not offered: The token is tied to one login and the API exposes only /my-campaigns, /category, /product and /sales (https://docs.kelkoogroup.com/for-advertisers/merchant-statistics-api/merchant-statistics-resources).
- ~~`update_budget`~~ not offered: The Merchant Statistics API is read-only statistics; budgets are managed in the Merchant Center (https://docs.kelkoogroup.com/for-advertisers/merchant-statistics-api/merchant-statistics-resources).
- ~~`pause_resume`~~ not offered: No write resource in the Merchant Statistics API (https://docs.kelkoogroup.com/for-advertisers/merchant-statistics-api/merchant-statistics-resources).

## Credentials

- `PLATFORM_MCP_KELKOO_GROUP_JWT` — Merchant Statistics API token (Kelkoo Merchant Center > API Credentials > Create new token; the JWT is shown once), sent as `Authorization: Bearer`. It reaches every campaign managed by the login.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve kelkoo_group   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve kelkoo_group
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve kelkoo_group   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kelkoo_group-mcp`. Python and TypeScript serve identical tools.
