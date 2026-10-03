# Adform FLOW MCP server

Category: **ads** · Docs: https://api.adform.com/help/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/adform.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/buyer/advertisers` (https://api.adform.com/v1/help/buyer/advertisers#!/Advertisers/get_v1_buyer_advertisers)
- `list_accounts` — `GET /v1/buyer/advertisers` (https://api.adform.com/v1/help/buyer/advertisers#!/Advertisers/get_v1_buyer_advertisers)
- `list_campaigns` — `GET /v1/buyer/campaigns` (https://api.adform.com/v1/help/buyer/campaigns#!/Campaigns/get_v1_buyer_campaigns)
- ~~`get_report`~~ not offered: Adform's Buyer Stats API is asynchronous: "POST /v1/buyer/stats/data — Order asynchronous report generation", then poll GET /v1/buyer/stats/operations/{id} and fetch GET /v1/buyer/stats/data/{id} (https://api.adform.com/v1/help/buyer/stats); the runtime has no report polling.
- ~~`update_budget`~~ not offered: Adform campaigns carry only a total planning `budget`, changed through the full-object "PUT /v1/buyer/campaigns/{id} — Updates a single campaign general details" (advertiserId, name, currency, dates, subType… required); there is no daily campaign budget.
- ~~`pause_resume`~~ not offered: "PUT /v1/buyer/campaigns/{id}/status — Activates or deactivates campaign" takes a bare JSON string body ("Active" / "Inactive"), which the adapter body builder cannot send (it builds JSON objects/arrays).

## Credentials

- `PLATFORM_MCP_ADFORM_CLIENT_ID` — Client id of an Adform API client enabled for the client-credentials flow (requested from Adform support; https://api.adform.com/help/guides/getting-started/authorization-guide).
- `PLATFORM_MCP_ADFORM_CLIENT_SECRET` — The client's secret, sent in the form body of POST https://id.adform.com/sts/connect/token; the client must be granted the buyer.advertisers.readonly and buyer.campaigns.api.readonly scopes. Tokens last about an hour and are re-requested automatically.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve adform   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve adform
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve adform   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/adform-mcp`. Python and TypeScript serve identical tools.
