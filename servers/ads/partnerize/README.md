# Partnerize MCP server

Category: **ads** · Docs: https://api-docs.partnerize.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/partnerize.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v3/brand` (https://api-docs.partnerize.com/brand/#operation/Get%20brands%20for%20a%20user)
- `list_accounts` — `GET /v3/brand` (https://api-docs.partnerize.com/brand/#operation/Get%20brands%20for%20a%20user)
- `list_campaigns` — `GET /user/advertiser/{account_id}/campaign` (https://api-docs.partnerize.com/brand/#operation/List%20all%20Brand%20Campaigns)
- `get_report` — `GET /reporting/report_advertiser/campaign/{campaign_id}/conversion.json` (https://api-docs.partnerize.com/brand/#operation/Retrieve%20a%20Brand%20Conversions%20Report)
- ~~`update_budget`~~ not offered: Partnerize campaigns are commission-based and have no budget attribute; PUT /campaign/{campaign_id} updates destination_url, title, terms and tracking settings (https://api-docs.partnerize.com/brand/#operation/Update%20a%20Campaign).
- ~~`pause_resume`~~ not offered: The campaign status (a/p/r/n) is not among the fields accepted by PUT /campaign/{campaign_id} (https://api-docs.partnerize.com/brand/#operation/Update%20a%20Campaign); there is no status endpoint.

## Credentials

- `PLATFORM_MCP_PARTNERIZE_APPLICATION_KEY` — Partnerize application_key (identifies the Network; Partnerize console > Settings > API credentials), the HTTP Basic username.
- `PLATFORM_MCP_PARTNERIZE_USER_API_KEY` — The user's user_api_key, the HTTP Basic password; results are limited to the user's brand permissions.

## Run

    uvx platform-mcp-hub serve partnerize          # Python
    npx -y platform-mcp-hub serve partnerize       # TypeScript
    claude mcp add partnerize -- uvx platform-mcp-hub serve partnerize

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/partnerize-mcp`. Python and TypeScript serve identical tools.
