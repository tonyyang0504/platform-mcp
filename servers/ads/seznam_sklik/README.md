# Seznam Sklik MCP server

Category: **ads** · Docs: https://api.sklik.cz/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/seznam_sklik.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user/me` (https://api.sklik.cz/fenix)
- `list_accounts` — `GET /user/linked-accounts` (https://api.sklik.cz/fenix)
- `list_campaigns` — `GET /sklik/campaigns/` (https://api.sklik.cz/fenix)
- `get_report` — `GET /sklik/campaigns/` (https://api.sklik.cz/fenix)
- `update_budget` — `PATCH /sklik/campaigns/{campaign_id}/` (https://api.sklik.cz/fenix)
- `pause_resume` — `PATCH /sklik/campaigns/{campaign_id}/` (https://api.sklik.cz/fenix)

## Credentials

- `PLATFORM_MCP_SEZNAM_SKLIK_REFRESH_TOKEN` — Sklik API Fénix refresh token (log in at https://www.sklik.cz/ > Tools > API > create token; you choose its validity and access level r / rw). Exchanged at POST https://api.sklik.cz/v1/user/token (grant_type=refresh_token, form) for a 1-hour access token, re-requested on expiry or 401; the token acts on the refresh token owner's own Sklik account.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve seznam_sklik   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve seznam_sklik
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve seznam_sklik   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/seznam_sklik-mcp`. Python and TypeScript serve identical tools.
