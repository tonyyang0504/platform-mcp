# StackAdapt MCP server

Category: **ads** · Docs: https://docs.stackadapt.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/stackadapt.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /advertisers` (https://docs.stackadapt.com/v2)
- `list_accounts` — `GET /advertisers` (https://docs.stackadapt.com/v2)
- `list_campaigns` — `GET /campaigns` (https://docs.stackadapt.com/v2)
- ~~`get_report`~~ not offered: GET /delivery (resource_type, type=total|daily|hourly, date_range_type=custom, start_date, end_date, group_by_resource) documents only a single total_stats object in its response; the shape of daily or grouped rows is not specified (https://www.stackadapt.com/service/v2/apidocs), and the GraphQL reporting reference is login-gated (https://docs.stackadapt.com/graphql).
- ~~`update_budget`~~ not offered: REST write operations are 'officially deprecated' (https://docs.stackadapt.com/: 'Migrate write integrations to the GraphQL API'), and the GraphQL reference that replaces them is login-gated (https://docs.stackadapt.com/graphql), so the current campaign-update mutation cannot be cited.
- ~~`pause_resume`~~ not offered: Same as update_budget: the REST PUT /campaign/{id} is deprecated and the GraphQL mutation reference is login-gated (https://docs.stackadapt.com/graphql). StackAdapt also publishes its own MCP server (https://docs.stackadapt.com/mcp-server) covering campaign management.

## Credentials

- `PLATFORM_MCP_STACKADAPT_REST_API_KEY` — StackAdapt REST API key (issued by StackAdapt on request), sent as the X-Authorization header. The GraphQL API uses a different Bearer token and is not used here.

## Run

    uvx platform-mcp-hub serve stackadapt          # Python
    npx -y platform-mcp-hub serve stackadapt       # TypeScript
    claude mcp add stackadapt -- uvx platform-mcp-hub serve stackadapt

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/stackadapt-mcp`. Python and TypeScript serve identical tools.
