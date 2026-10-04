# impact.com MCP server

Category: **ads** · Docs: https://integrations.impact.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/impact_com.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /CompanyInformation` (https://integrations.impact.com/brand-api-reference/reference/accounts/company-information)
- `list_campaigns` — `GET /Campaigns` (https://integrations.impact.com/brand-api-reference/reference/programs/programs)
- `get_report` — `GET /Reports/{report_id}` (https://integrations.impact.com/brand-api-reference/reference/report-export/reports-legacy)
- ~~`list_accounts`~~ not offered: API tokens are per account: every path is /Advertisers/{AccountSID}/… and the Brand API has no account list (https://integrations.impact.com/brand-api-reference/readme/authentication).
- ~~`update_budget`~~ not offered: impact.com programs are pay-per-action and have no budget attribute (Program schema, https://integrations.impact.com/brand-api-reference/reference/programs/programs).
- ~~`pause_resume`~~ not offered: The Programs API is read-only (List All Programs, Get Program Details); program State cannot be changed through the Brand API (https://integrations.impact.com/brand-api-reference/reference/programs/programs).

## Credentials

- `PLATFORM_MCP_IMPACT_COM_ACCOUNT_SID` — Account SID of a Brand API access token (impact.com > user profile > Settings > Technical > API > Create Access Token); the HTTP Basic username and the {AccountSID} in every path.
- `PLATFORM_MCP_IMPACT_COM_AUTH_TOKEN` — The token's Auth Token, the HTTP Basic password. Needs read scope for programs and reports.
- `PLATFORM_MCP_IMPACT_COM_REPORT_ID` — Report handle for get_report, taken from GET /Advertisers/{AccountSID}/Reports (Id of a report with ApiAccessible=true, e.g. a performance-by-day report); its columns are listed by /Reports/{ReportId}/MetaData.

## Run

    uvx platform-mcp-hub serve impact_com          # Python
    npx -y platform-mcp-hub serve impact_com       # TypeScript
    claude mcp add impact_com -- uvx platform-mcp-hub serve impact_com

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/impact_com-mcp`. Python and TypeScript serve identical tools.
