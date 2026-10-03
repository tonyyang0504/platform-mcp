# Yandex Direct (Яндекс Директ) MCP server

Category: **ads** · Docs: https://yandex.com/dev/direct/doc/en/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/yandex_direct.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /clients` (https://yandex.com/dev/direct/doc/en/clients/get)
- `list_accounts` — `POST /clients` (https://yandex.com/dev/direct/doc/en/clients/get)
- `list_campaigns` — `POST /campaigns` (https://yandex.com/dev/direct/doc/en/campaigns/get)
- `pause_resume` — `POST /campaigns` (https://yandex.com/dev/direct/doc/en/campaigns/suspend)
- ~~`get_report`~~ not offered: Yandex Direct statistics come from the Reports service, which returns TSV text (not JSON) and may answer 201/202 while a report is built offline (https://yandex.com/dev/direct/doc/reports/reports); the runtime maps JSON only and has no report polling.
- ~~`update_budget`~~ not offered: Campaign daily budgets are micro-units ("DailyBudget.Amount (long)" in the currency multiplied by 1,000,000, POST /json/v5/campaigns method update, https://yandex.com/dev/direct/doc/en/campaigns/update); the adapter cannot scale a daily_budget into micros.

## Credentials

- `PLATFORM_MCP_YANDEX_DIRECT_TOKEN` — Yandex OAuth token of the Direct user (app registered at oauth.yandex.com with Direct API access approved; https://yandex.com/dev/direct/doc/en/concepts/auth-token), sent as Authorization: Bearer.
- `PLATFORM_MCP_YANDEX_DIRECT_CLIENT_LOGIN` — Advertiser login to act for, sent as the Client-Login header (required for agency and representative tokens; omit for a direct advertiser).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve yandex_direct   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve yandex_direct
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve yandex_direct   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/yandex_direct-mcp`. Python and TypeScript serve identical tools.
